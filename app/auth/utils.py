import os
import sys
import string
import random
import hashlib
import json
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from alibabacloud_dypnsapi20170525.client import Client as DypnsClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dypnsapi20170525 import models as dypns_models
from alibabacloud_tea_util import models as util_models

try:
    from config import (
        EMAIL_CONFIG, ALIYUN_SMS_CONFIG, TURNSTILE_CONFIG,
        RISK_CONTROL, IP_LOCATION_API
    )
    from app.env_config import configure_turnstile, configure_risk_control
except ImportError:
    print("错误：请复制 config.example.py 为 config.py 并配置相关参数！")
    sys.exit(1)

turnstile_config = configure_turnstile()
risk_control = configure_risk_control()

TURNSTILE_SECRET_KEY = TURNSTILE_CONFIG['secret_key']
TURNSTILE_VERIFY_URL = TURNSTILE_CONFIG['verify_url']
TURNSTILE_ENABLED = turnstile_config['enabled']

ALIBABA_CLOUD_ACCESS_KEY_ID = ALIYUN_SMS_CONFIG['access_key_id']
ALIBABA_CLOUD_ACCESS_KEY_SECRET = ALIYUN_SMS_CONFIG['access_key_secret']
ALIBABA_CLOUD_SIGN_NAME = ALIYUN_SMS_CONFIG['sign_name']
ALIBABA_CLOUD_TEMPLATE_CODE = ALIYUN_SMS_CONFIG['template_code']


def generate_user_id():
    """生成15位字母数字混合的用户ID"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(15))


def get_network_time():
    try:
        import urllib.request
        url = "https://www.baidu.com"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            date_str = response.headers.get('Date')
            if date_str:
                from email.utils import parsedate_to_datetime
                dt_gmt = parsedate_to_datetime(date_str)
                dt = dt_gmt + timedelta(hours=8)
                print(f"获取网络时间成功 (百度HTTP): {dt}")
                return dt
    except Exception as e:
        print(f"百度HTTP头部获取失败: {e}")

    try:
        import urllib.request
        url = "http://worldtimeapi.org/api/timezone/Asia/Shanghai"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            datetime_str = data['datetime']
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            print(f"获取网络时间成功 (WorldTimeAPI): {dt}")
            return dt
    except Exception as e:
        print(f"WorldTimeAPI获取失败: {e}")

    try:
        import urllib.request
        url = "https://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            timestamp_ms = int(data['data']['t'])
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            print(f"获取网络时间成功 (淘宝API): {dt}")
            return dt
    except Exception as e:
        print(f"淘宝API获取失败: {e}")

    try:
        import urllib.request
        url = "https://cgi.im.qq.com/cgi-bin/cgi_svrtime"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            import re
            match = re.search(r'var svrtime = (\d+);', content)
            if match:
                timestamp = int(match.group(1))
                dt = datetime.fromtimestamp(timestamp)
                print(f"获取网络时间成功 (QQ API): {dt}")
                return dt
    except Exception as e:
        print(f"QQ API获取失败: {e}")

    raise RuntimeError("无法获取在线时间，请检查网络连接后重试")


def get_network_timestamp():
    dt = get_network_time()
    return dt.timestamp()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))


def is_password_strong(password):
    if len(password) <= 6:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char.islower() for char in password):
        return False
    if not any(not char.isalnum() for char in password):
        return False
    return True


def verify_turnstile(token, remote_ip):
    if not TURNSTILE_ENABLED:
        print("开发模式：跳过Turnstile验证")
        return True

    try:
        data = urllib.parse.urlencode({
            'secret': TURNSTILE_SECRET_KEY,
            'response': token,
            'remoteip': remote_ip
        }).encode()

        req = urllib.request.Request(
            TURNSTILE_VERIFY_URL,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())

        return result.get('success', False)
    except Exception as e:
        print(f"Turnstile验证失败: {e}")
        return False


def parse_user_agent(user_agent):
    import re
    browser = '未知浏览器'
    device = '电脑端'

    if 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent:
        device = '手机端'

    if 'Chrome' in user_agent and 'Edg' not in user_agent:
        browser = f'Chrome ({device})'
    elif 'Firefox' in user_agent:
        browser = f'Firefox ({device})'
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        browser = f'Safari ({device})'
    elif 'Edg' in user_agent:
        browser = f'Edge ({device})'
    else:
        browser = f'其他浏览器 ({device})'

    return browser


def get_ip_location(ip):
    if ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.'):
        return '内网地址'
    return '未知位置'


def check_login_risk(user_id, current_ip, current_place, conn):
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ip, place FROM login_log
            WHERE `user-id` = %s
            ORDER BY time DESC
            LIMIT 5
        """, (user_id,))
        recent_logins = cursor.fetchall()

        cursor.close()

        if not recent_logins:
            return 0

        known_ips = {login[0] for login in recent_logins if login[0]}
        if current_ip not in known_ips:
            return 1

        known_places = {login[1] for login in recent_logins if login[1]}
        if current_place not in known_places and current_place != '未知位置' and current_place != '内网地址':
            return 1

        return 0
    except Exception as e:
        print(f"风控判断失败: {e}")
        return 0


def send_verification_email(email, code):
    print(f'[邮件发送] 开始发送注册验证码邮件到: {email}')
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = email
        msg['Subject'] = 'SNYQT统一账户服务平台 注册验证码'

        body = f"""
        尊敬的用户：

        您正在注册SNYQT统一账户服务平台，您的验证码是：{code}

        请在5分钟内使用此验证码完成注册，如非本人操作，请忽略此邮件。

        SNYQT团队
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        print(f'[邮件发送] 正在连接SMTP服务器: {EMAIL_CONFIG["smtp_server"]}:{EMAIL_CONFIG["port"]}')
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port'])
        server.starttls()
        print(f'[邮件发送] SMTP连接成功，正在登录...')
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        text = msg.as_string()
        print(f'[邮件发送] 正在发送邮件...')
        server.sendmail(EMAIL_CONFIG['sender'], email, text)
        server.quit()
        print(f'[邮件发送] 邮件发送成功！')

        return True, None
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f'SMTP认证失败: {str(e)}'
        print(f'[邮件发送] {error_msg}')
        return False, error_msg
    except smtplib.SMTPConnectError as e:
        error_msg = f'SMTP连接失败: {str(e)}'
        print(f'[邮件发送] {error_msg}')
        return False, error_msg
    except smtplib.SMTPException as e:
        error_msg = f'SMTP错误: {str(e)}'
        print(f'[邮件发送] {error_msg}')
        return False, error_msg
    except Exception as e:
        error_msg = f'发送邮件失败: {str(e)}'
        print(f'[邮件发送] {error_msg}')
        import traceback
        traceback.print_exc()
        return False, error_msg


def send_2fa_verification_email(email, code):
    print(f'[二次验证邮件] 开始发送二次验证邮件到: {email}')
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = email
        msg['Subject'] = 'SNYQT统一账户服务平台 登录验证'

        body = f"""
        尊敬的用户：

        您的账号检测到异常登录，请使用以下验证码完成登录：{code}

        请在5分钟内使用此验证码完成登录，如非本人操作，请忽略此邮件。

        SNYQT团队
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        print(f'[二次验证邮件] 正在连接SMTP服务器: {EMAIL_CONFIG["smtp_server"]}:{EMAIL_CONFIG["port"]}')
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port'])
        server.starttls()
        print(f'[二次验证邮件] SMTP连接成功，正在登录...')
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        text = msg.as_string()
        print(f'[二次验证邮件] 正在发送邮件...')
        server.sendmail(EMAIL_CONFIG['sender'], email, text)
        server.quit()
        print(f'[二次验证邮件] 邮件发送成功！')

        return True, None
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f'SMTP认证失败: {str(e)}'
        print(f'[二次验证邮件] {error_msg}')
        return False, error_msg
    except smtplib.SMTPConnectError as e:
        error_msg = f'SMTP连接失败: {str(e)}'
        print(f'[二次验证邮件] {error_msg}')
        return False, error_msg
    except smtplib.SMTPException as e:
        error_msg = f'SMTP错误: {str(e)}'
        print(f'[二次验证邮件] {error_msg}')
        return False, error_msg
    except Exception as e:
        error_msg = f'发送二次验证邮件失败: {str(e)}'
        print(f'[二次验证邮件] {error_msg}')
        import traceback
        traceback.print_exc()
        return False, error_msg


def create_client():
    config = open_api_models.Config(
        access_key_id=ALIBABA_CLOUD_ACCESS_KEY_ID,
        access_key_secret=ALIBABA_CLOUD_ACCESS_KEY_SECRET
    )
    config.endpoint = 'dypnsapi.aliyuncs.com'
    return DypnsClient(config)


def send_sms(phone_numbers):
    pure_phone = ''.join(c for c in phone_numbers if c.isdigit() or c == '+')

    client = create_client()
    code = generate_verification_code()
    print(f'生成的验证码: {code}')

    send_sms_request = dypns_models.SendSmsVerifyCodeRequest(
        phone_number=pure_phone,
        sign_name=ALIBABA_CLOUD_SIGN_NAME,
        template_code=ALIBABA_CLOUD_TEMPLATE_CODE,
        template_param=f'{{"code":"{code}","min":"5"}}'
    )
    runtime = util_models.RuntimeOptions()
    try:
        resp = client.send_sms_verify_code_with_options(send_sms_request, runtime)
        print(f'短信发送响应: {resp}')
        print(f'响应Body: {resp.body}')
        print(f'resp.body.code: {resp.body.code}')

        return True, None, code
    except Exception as e:
        print(f'发送短信失败: {e}')
        import traceback
        traceback.print_exc()
        return True, None, code


def check_sms_code(phone_number, verify_code):
    pure_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+')

    client = create_client()
    check_request = dypns_models.CheckSmsVerifyCodeRequest(
        phone_number=pure_phone,
        verify_code=verify_code
    )
    runtime = util_models.RuntimeOptions()
    try:
        resp = client.check_sms_verify_code_with_options(check_request, runtime)
        print(f'验证码核验响应: {resp}')
        print(f'响应Body: {resp.body}')
        if resp.body.code == 'OK':
            verify_result = resp.body.verify_result
            return verify_result, None
        else:
            return False, resp.body.message
    except Exception as e:
        print(f'核验验证码失败: {e}')
        import traceback
        traceback.print_exc()
        return False, str(e)
