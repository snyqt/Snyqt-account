# -*- coding: utf-8 -*-
"""
MFA 多因子认证模块
- TOTP (Authenticator App / Google Authenticator)
- WebAuthn (安全密钥 / FIDO2)
"""

import json
import base64
import io
import pyotp
import qrcode
import pymysql
from datetime import datetime
from flask import request, jsonify, session, render_template, current_app
from werkzeug.security import check_password_hash

from app.mfa import mfa_bp
from app.models.db import get_db_connection

# ── WebAuthn 配置 ──
RP_ID = 'account.snyqt.top'
RP_NAME = '少年友晴天-统一账户认证系统'
ORIGIN = 'https://account.snyqt.top'

# ── 认证登录装饰器 ──
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({'success': False, 'message': '用户未登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ════════════════════════════════════════════════════════════════
#  TOTP (Authenticator App) 部分
# ════════════════════════════════════════════════════════════════

@mfa_bp.route('/totp/status')
@login_required
def totp_status():
    """获取 TOTP 绑定状态"""
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT totp_secret, totp_enabled FROM user_info WHERE id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return jsonify({
                'success': True,
                'totp_enabled': bool(row[1]),
                'has_secret': bool(row[0])
            })
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@mfa_bp.route('/totp/setup', methods=['POST'])
@login_required
def totp_setup():
    """生成 TOTP 密钥和二维码（绑定前需要验证密码）"""
    user_id = session['user_id']
    data = request.get_json()
    password = data.get('password', '')

    if not password:
        return jsonify({'success': False, 'message': '请输入密码确认身份'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT password, Name, totp_secret, totp_enabled FROM user_info WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        # 验证密码
        pw_hash = user['password']
        if not check_password_hash(pw_hash, password):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '密码错误'}), 403

        if user['totp_enabled']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '已绑定 TOTP，请先解绑再重新绑定'}), 400

        # 生成新的 TOTP 密钥
        secret = pyotp.random_base32()
        username = user['Name']
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name='Snyqt Account'
        )

        # 生成二维码图片（base64）
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        # 暂存密钥到 session（确认后才写入数据库）
        session['mfa_totp_secret'] = secret
        session.permanent = True

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'secret': secret,
            'qr_code': f'data:image/png;base64,{qr_base64}',
            'message': '请使用 Authenticator App 扫描二维码，然后输入验证码确认'
        })
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@mfa_bp.route('/totp/verify-setup', methods=['POST'])
@login_required
def totp_verify_setup():
    """验证 TOTP 验证码并启用"""
    user_id = session['user_id']
    data = request.get_json()
    code = data.get('code', '')

    secret = session.get('mfa_totp_secret')
    if not secret:
        return jsonify({'success': False, 'message': '绑定会话已过期，请重新生成'}), 400

    if not code or len(code) != 6:
        return jsonify({'success': False, 'message': '请输入6位验证码'}), 400

    # 验证 TOTP 码
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        return jsonify({'success': False, 'message': '验证码错误，请重试'}), 400

    # 写入数据库
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_info SET totp_secret = %s, totp_enabled = 1 WHERE id = %s",
            (secret, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        session.pop('mfa_totp_secret', None)
        return jsonify({'success': True, 'message': 'TOTP 绑定成功'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@mfa_bp.route('/totp/disable', methods=['POST'])
@login_required
def totp_disable():
    """解绑 TOTP（需要验证密码）"""
    user_id = session['user_id']
    data = request.get_json()
    password = data.get('password', '')
    code = data.get('code', '')

    if not password:
        return jsonify({'success': False, 'message': '请输入密码确认身份'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT password, totp_secret, totp_enabled FROM user_info WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        if not check_password_hash(user['password'], password):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '密码错误'}), 403

        if not user['totp_enabled']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '尚未绑定 TOTP'}), 400

        # 如果提供了验证码，先验证
        if code:
            totp = pyotp.TOTP(user['totp_secret'])
            if not totp.verify(code, valid_window=1):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '验证码错误'}), 400

        cursor.execute(
            "UPDATE user_info SET totp_secret = NULL, totp_enabled = 0 WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'TOTP 已解绑'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ════════════════════════════════════════════════════════════════
#  WebAuthn (安全密钥) 部分
# ════════════════════════════════════════════════════════════════

@mfa_bp.route('/webauthn/keys')
@login_required
def webauthn_keys():
    """列出已注册的安全密钥"""
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT id, credential_id, name, sign_count, created_at FROM security_keys WHERE user_id = %s",
            (user_id,)
        )
        keys = cursor.fetchall()
        for k in keys:
            if k['created_at']:
                k['created_at'] = k['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'keys': keys})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@mfa_bp.route('/webauthn/register/begin', methods=['POST'])
@login_required
def webauthn_register_begin():
    """开始注册安全密钥"""
    user_id = session['user_id']
    username = session.get('username', '')

    try:
        from webauthn.registration.generate_registration_options import generate_registration_options
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria,
            PublicKeyCredentialDescriptor,
            UserVerificationRequirement,
        )

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT credential_id FROM security_keys WHERE user_id = %s",
            (user_id,)
        )
        existing = cursor.fetchall()
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=bytes.fromhex(k['credential_id']))
            for k in existing
        ]
        cursor.close()
        conn.close()

        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user_id.encode('utf-8'),
            user_name=username,
            user_display_name=username,
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        # 存储 challenge 到 session（Flask session 不能存 bytes，转 base64）
        session['mfa_webauthn_challenge'] = base64.b64encode(options.challenge).decode('utf-8')
        session.permanent = True

        return jsonify({
            'success': True,
            'options': json.loads(options.json())
        })
    except ImportError:
        return jsonify({'success': False, 'message': 'webauthn 库未安装'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@mfa_bp.route('/webauthn/register/complete', methods=['POST'])
@login_required
def webauthn_register_complete():
    """完成注册安全密钥"""
    user_id = session['user_id']
    challenge_b64 = session.get('mfa_webauthn_challenge')
    if not challenge_b64:
        return jsonify({'success': False, 'message': '注册会话已过期'}), 400
    challenge = base64.b64decode(challenge_b64)

    try:
        from webauthn.registration.verify_registration_response import verify_registration_response

        data = request.get_json()

        verification = verify_registration_response(
            credential=data,
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
        )

        credential_id_hex = verification.credential_id.hex()
        public_key_b64 = base64.b64encode(verification.credential_public_key).decode('utf-8')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor()
        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM security_keys WHERE credential_id = %s AND user_id = %s",
            (credential_id_hex, user_id)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '该安全密钥已注册'}), 400

        cursor.execute(
            "INSERT INTO security_keys (user_id, credential_id, public_key, name, sign_count, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, credential_id_hex, public_key_b64,
             f'安全密钥 #{credential_id_hex[:6]}',
             verification.sign_count,
             datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()

        session.pop('mfa_webauthn_challenge', None)
        return jsonify({'success': True, 'message': '安全密钥注册成功'})
    except ImportError:
        return jsonify({'success': False, 'message': 'webauthn 库未安装'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'注册失败: {str(e)}'}), 500


@mfa_bp.route('/webauthn/auth/begin', methods=['POST'])
def webauthn_auth_begin():
    """开始安全密钥认证（登录时使用）"""
    try:
        from webauthn.authentication.generate_authentication_options import generate_authentication_options
        from webauthn.helpers.structs import PublicKeyCredentialDescriptor

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 如果已登录，直接用当前用户；否则使用 pending 用户
        if 'logged_in' in session and session['logged_in']:
            user_id = session['user_id']
        elif 'pending_user_id' in session:
            user_id = session['pending_user_id']
        else:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '请先登录'}), 401

        cursor.execute(
            "SELECT credential_id FROM security_keys WHERE user_id = %s",
            (user_id,)
        )
        keys = cursor.fetchall()
        cursor.close()
        conn.close()

        if not keys:
            return jsonify({'success': False, 'message': '未注册安全密钥'}), 404

        allow_credentials = [
            PublicKeyCredentialDescriptor(id=bytes.fromhex(k['credential_id']))
            for k in keys
        ]

        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=allow_credentials,
        )

        session['mfa_webauthn_challenge'] = base64.b64encode(options.challenge).decode('utf-8')
        session.permanent = True

        return jsonify({
            'success': True,
            'options': json.loads(options.json())
        })
    except ImportError:
        return jsonify({'success': False, 'message': 'webauthn 库未安装'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@mfa_bp.route('/webauthn/auth/complete', methods=['POST'])
def webauthn_auth_complete():
    """完成安全密钥认证"""
    challenge_b64 = session.get('mfa_webauthn_challenge')
    if not challenge_b64:
        return jsonify({'success': False, 'message': '认证会话已过期'}), 400
    challenge = base64.b64decode(challenge_b64)

    try:
        from webauthn.authentication.verify_authentication_response import verify_authentication_response

        data = request.get_json()
        raw_id_b64 = data.get('rawId', '')
        credential_id_hex = base64.urlsafe_b64decode(raw_id_b64 + '==' * (-len(raw_id_b64) % 4)).hex()

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT public_key, sign_count FROM security_keys WHERE credential_id = %s",
            (credential_id_hex,)
        )
        key = cursor.fetchone()

        if not key:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '未知安全密钥'}), 404

        verification = verify_authentication_response(
            credential=data,
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=base64.b64decode(key['public_key']),
            credential_current_sign_count=key['sign_count'],
        )

        # 更新签名计数器
        cursor.execute(
            "UPDATE security_keys SET sign_count = %s WHERE credential_id = %s",
            (verification.new_sign_count, credential_id_hex)
        )
        conn.commit()
        cursor.close()
        conn.close()

        session.pop('mfa_webauthn_challenge', None)
        return jsonify({'success': True, 'message': '安全密钥认证成功'})
    except ImportError:
        return jsonify({'success': False, 'message': 'webauthn 库未安装'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'认证失败: {str(e)}'}), 500


@mfa_bp.route('/webauthn/key/<int:key_id>', methods=['DELETE'])
@login_required
def webauthn_delete_key(key_id):
    """删除已注册的安全密钥（需要密码确认）"""
    user_id = session['user_id']
    data = request.get_json() or {}
    password = data.get('password', '')

    if not password:
        return jsonify({'success': False, 'message': '请输入密码确认身份'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT password FROM user_info WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        if not user or not check_password_hash(user['password'], password):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '密码错误'}), 403

        cursor.execute(
            "DELETE FROM security_keys WHERE id = %s AND user_id = %s",
            (key_id, user_id)
        )
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': '密钥不存在或无权删除'}), 404

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': '安全密钥已删除'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ════════════════════════════════════════════════════════════════
#  MFA 设置页面
# ════════════════════════════════════════════════════════════════

@mfa_bp.route('/settings')
@login_required
def mfa_settings_page():
    """MFA 设置页面"""
    return render_template('mfa_settings.html')