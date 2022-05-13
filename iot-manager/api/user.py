import re
import time
import logging

from flask import Flask, jsonify, request
from flask_cors import *
from common.md5_operate import get_md5
from common.mysql_operate import db
from common.redis_operate import redis_db

app = Flask(__name__)
CORS(app, supports_credentials=True)  # 解决跨域问题
app.config["JSON_AS_ASCII"] = False  # jsonify返回的中文正常显示

"""devices api"""


@app.route("/devices", methods=["GET"])
def get_all_devices():
    """获取所有设备信息"""
    sql = "SELECT * FROM device"
    data = db.select_db(sql)
    print("获取所有设备信息 == >> {}".format(data))
    return jsonify({"code": 0, "data": data, "msg": "查询成功"})


@app.route("/adddevice", methods=["POST"])
def insert_device():
    """添加设备"""
    print("request:{}", request)
    uid = request.values.get("uid", "").strip()  # uid
    print("uid", uid)
    name = request.values.get("name", "").strip()  # name
    print("uid", name)
    key = request.values.get("key", "").strip()  # key
    print("key", key)

    if uid and key:
        key_md5 = get_md5(uid, key)  # 将key进行md5加密
        sql1 = "SELECT name FROM device WHERE uid = '{}'".format(uid)
        res1 = db.select_db(sql1)
        if res1:
            return jsonify({"code": 2002, "msg": "设备已存在，添加失败！！！"})
        else:
            sql2 = "INSERT INTO device(uid, name, `key`) " \
                   "VALUES('{}', '{}', '{}')".format(uid, name, key_md5)
            db.execute_db(sql2)
            print("新增设备信息SQL ==>> {}".format(sql2))
            return jsonify({"code": 0, "key": key_md5, "msg": "恭喜，设备添加成功！"})  # 将加密后的key返回

    else:
        return jsonify({"code": 2001, "msg": "设备uid或key不能为空"})


@app.route("/update_action", methods=["POST"])
def update_device():
    """更新设备操作接口"""
    """数据库内status==1，用户已操作，待设备执行"""
    """数据库内status==0，用户未操作，用户可操作"""
    print("request:{}", request)
    uid = request.values.get("uid", "").strip()  # uid
    print("uid", uid)

    key = request.values.get("key", "").strip()  # key 为已加密过的key
    print("key", key)

    action = request.values.get("action", "").strip()  # action 可执行操作
    print("action", action)

    status = request.values.get("status", "").strip()  # action 用户操作
    print("status", status)

    if status=='':
        return jsonify({"code": 2002, "msg": "status不可为空"})
    if uid and key:
        sql1 = "SELECT * FROM device WHERE uid = '{}' and `key` = '{}' ".format(uid, key)
        print("SQL ==>> {}".format(sql1))
        res1 = db.select_db(sql1)
        print(format(res1))
        if res1:
            sql2 = "SELECT status FROM device WHERE uid = {} and action = '{}' ".format(uid, action)
            print("SQL ==>> {}".format(sql2))

            res2 = db.select_db(sql2)
            print(format(res2))
            if res2:  # 该操作指令存在
                if res2[0]["status"] == 1:  # 该行为之前已被操作
                    return jsonify({"code": 2004, "msg": "该操作已经记录，无需重复操作"})
                else:  # 该操作将被记录
                    sql3 = "UPDATE device SET status = '{}'" \
                           "WHERE uid = {}".format(status, uid)
                    db.execute_db(sql3)
                    return jsonify({"code": 0, "msg": "该操作记录成功，等待设备接入更新"})

            else:  # 该操作不存在
                return jsonify({"code": 2003, "msg": "该操作已不存在，请重新获取可操作指令"})

        else:
            return jsonify({"code": 2002, "msg": "设备不存在，请检查uid或key"})

    else:
        return jsonify({"code": 2001, "msg": "设备uid或key不能为空"})


@app.route("/upload", methods=["POST"])
def upload():
    """openAPI，设备上传信息接口"""
    """数据库内status==true，用户已操作，待设备执行"""
    """数据库内status==false，用户未操作，用户可操作"""

    print("request:{}", request)
    uid = request.values.get("uid", "").strip()  # uid
    print("uid", uid)
    name = request.values.get("name", "").strip()  # name
    print("uid", name)
    key = request.values.get("key", "").strip()  # key 为已加密过的key
    print("key", key)

    msg = request.values.get("msg", "").strip()  # msg 设备信息
    print("msg", msg)

    action = request.values.get("action", "").strip()  # action 设备当前可执行操作
    print("action", action)

    # 判断设备是否已添加过，只有添加过的设备才能上传信息

    if uid and key:
        sql1 = "SELECT * FROM device WHERE uid = '{}' and `key` = '{}'".format(uid, key)
        res1 = db.select_db(sql1)
        if res1:
            status = 0
            sql2 = "SELECT action,status FROM device WHERE uid = '{}' and `key` = '{}'".format(uid, key)
            res2 = db.select_db(sql2)
            if action == res2[0]["action"]:  # 当前可操作与数据库存储可操作一样，则判断用户是否已选择操作
                if res2[0]["status"] == 1:  # status为true，表明用户已执行操作，需要操作
                    status = 0  # 设备执行操作，并更新库为已未操作
                    sql3 = "UPDATE device SET msg = '{}', status = '{}' " \
                           "WHERE uid = {}".format(msg, status, uid)
                    db.execute_db(sql3)
                    return jsonify({"code": 1001, "action": action, "msg": "信息已更新，需要执行操作"})

                else:  # 用户未操作,只更新msg即可
                    sql5 = "UPDATE device SET msg = '{}'" \
                           "WHERE uid = {}".format(msg, uid)
                    db.execute_db(sql5)
                    return jsonify({"code": 1000, "action": "", "msg": "信息已更新，无需执行操作"})

            else:  # 当前可执行操作与库里操作不一致，则更新可执行操作，默认未执行
                status = 0
                sql4 = "UPDATE device SET msg = '{}', action = '{}',status = '{}' " \
                       "WHERE uid = {}".format(msg, action, status, uid)
                db.execute_db(sql4)

                return jsonify({"code": 0, "action": action, "msg": "信息已更新"})

        else:
            return jsonify({"code": 2002, "msg": "设备不存在，请检查uid或key或添加设备"})

    else:
        return jsonify({"code": 2001, "msg": "设备uid或key不能为空"})


"""user api"""


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route("/users", methods=["GET"])
def get_all_users():
    """获取所有用户信息"""
    sql = "SELECT id,username,role,telephone FROM user"
    data = db.select_db(sql)
    print("获取所有用户信息 == >> {}".format(data))
    return jsonify({"code": 0, "data": data, "msg": "查询成功"})


@app.route("/users/<string:username>", methods=["GET"])
def get_user(username):
    """获取某个用户信息"""
    sql = "SELECT * FROM user WHERE username = '{}'".format(username)
    data = db.select_db(sql)
    print("获取 {} 用户信息 == >> {}".format(username, data))
    if data:
        return jsonify({"code": 0, "data": data, "msg": "查询成功"})
    return jsonify({"code": "1004", "msg": "查不到相关用户的信息"})


@app.route("/register", methods=['POST'])
def user_register():
    """注册用户"""
    print("request:{}", request)
    username = request.values.get("username", "").strip()  # 用户名
    print("username", username)
    password = request.values.get("password", "").strip()  # 密码
    print("password", password)
    role = request.values.get("role", "").strip()  # 角色
    print("role", role)
    #  sex = request.json.get("sex", "0").strip()  # 性别，默认为0(男性)
    telephone = request.values.get("telephone", "").strip()  # 手机号
    print("telephone", telephone)
    # address = request.json.get("address", "").strip()  # 地址，默认为空串
    if username and password and telephone:  # 注意if条件中 "" 也是空, 按False处理
        sql1 = "SELECT username FROM user WHERE username = '{}'".format(username)
        res1 = db.select_db(sql1)
        print("查询到用户名 ==>> {}".format(res1))
        sql2 = "SELECT telephone FROM user WHERE telephone = '{}'".format(telephone)
        res2 = db.select_db(sql2)
        print("查询到手机号 ==>> {}".format(res2))
        if res1:
            return jsonify({"code": 2002, "msg": "用户名已存在，注册失败！！！"})
        # elif not (sex == "0" or sex == "1"):
        # return jsonify({"code": 2003, "msg": "输入的性别只能是 0(男) 或 1(女)！！！"})
        elif not (len(telephone) == 11 and re.match("^1[3,5,7,8]\d{9}$", telephone)):
            return jsonify({"code": 2004, "msg": "手机号格式不正确！！！"})
        elif res2:
            return jsonify({"code": 2005, "msg": "手机号已被注册！！！"})
        else:
            password = get_md5(username, password)  # 把传入的明文密码通过MD5加密变为密文，然后再进行注册
            sql3 = "INSERT INTO user(username, password, role, telephone) " \
                   "VALUES('{}', '{}', '{}', '{}')".format(username, password, role, telephone)
            db.execute_db(sql3)
            print("新增用户信息SQL ==>> {}".format(sql3))
            return jsonify({"code": 0, "msg": "恭喜，注册成功！"})
    else:
        return jsonify({"code": 2001, "msg": "用户名/密码/手机号不能为空，请检查！！！"})


@app.route("/login", methods=['POST'])
def user_login():
    """登录用户"""
    print("登录request", request)
    username = request.values.get("username", "").strip()
    password = request.values.get("password", "").strip()
    # request.values.get("token", "").strip()
    # role = request.values.get("role", "".strip())
    if username and password:  # 注意if条件中空串 "" 也是空, 按False处理
        sql1 = "SELECT username FROM user WHERE username = '{}'".format(username)
        res1 = db.select_db(sql1)
        logging.info("请求信息是：usnername-{}".format(username))
        print("查询到用户名 ==>> {}".format(res1))
        if not res1:
            return jsonify({"code": 1003, "msg": "用户名不存在！！！"})
        md5_password = get_md5(username, password)  # 把传入的明文密码通过MD5加密变为密文
        sql2 = "SELECT * FROM user WHERE username = '{}' and password = '{}'".format(username, md5_password)
        res2 = db.select_db(sql2)
        print("获取 {} 用户信息 == >> {}".format(username, res2))
        if res2:
            timeStamp = int(time.time())  # 获取当前时间戳
            # token = "{}{}".format(username, timeStamp)
            token = get_md5(username, str(timeStamp))  # MD5加密后得到token
            redis_db.handle_redis_token(username, token)  # 把token放到redis中存储
            login_info = {  # 构造一个字段，将 id/username/token/login_time 返回
                "id": res2[0]["id"],
                "role": res2[0]["role"],
                "username": username,
                "token": token,
                "login_time": time.strftime("%Y/%m/%d %H:%M:%S")
            }
            return jsonify({"status": 1, "code": 0, "login_info": login_info, "msg": "恭喜，登录成功！"}), 200, [
                ("Access-Control-Allow-Origin", "*")]
        return jsonify({"status": -1, "code": 1002, "msg": "用户名或密码错误！！！"})
    else:
        return jsonify({"status": 0, "code": 1001, "msg": "用户名或密码不能为空！！！"})


@app.route("/update/user/<int:id>", methods=['PUT'])
def user_update(id):  # id为准备修改的用户ID
    """修改用户信息"""
    admin_user = request.values.get("admin_user", "").strip()  # 当前登录的管理员用户
    token = request.values.get("token", "").strip()  # token口令
    new_password = request.values.get("password", "").strip()  # 新的密码
    # new_sex = request.json.get("sex", "0").strip()  # 新的性别，如果参数不传sex，那么默认为0(男性)
    new_telephone = request.values.get("telephone", "").strip()  # 新的手机号
    # new_address = request.json.get("address", "").strip()  # 新的联系地址，默认为空串
    if admin_user and token and new_password and new_telephone:  # 注意if条件中空串 "" 也是空, 按False处理
        # if not (new_sex == "0" or new_sex == "1"):
        # return jsonify({"code": 4007, "msg": "输入的性别只能是 0(男) 或 1(女)！！！"})
        if not (len(new_telephone) == 11 and re.match("^1[3,5,7,8]\d{9}$", new_telephone)):
            return jsonify({"code": 4008, "msg": "手机号格式不正确！！！"})
        else:
            redis_token = redis_db.handle_redis_token(admin_user)  # 从redis中取token
            if redis_token:
                if redis_token == token:  # 如果从redis中取到的token不为空，且等于请求body中的token
                    sql1 = "SELECT role FROM user WHERE username = '{}'".format(admin_user)
                    res1 = db.select_db(sql1)
                    print("根据用户名 【 {} 】 查询到用户类型 == >> {}".format(admin_user, res1))
                    user_role = res1[0]["role"]
                    if user_role == 0:  # 如果当前登录用户是管理员用户
                        sql2 = "SELECT * FROM user WHERE id = '{}'".format(id)
                        res2 = db.select_db(sql2)
                        print("根据用户ID 【 {} 】 查询到用户信息 ==>> {}".format(id, res2))
                        sql3 = "SELECT telephone FROM user WHERE telephone = '{}'".format(new_telephone)
                        res3 = db.select_db(sql3)
                        print("返回结果：{}".format(res3))
                        print("查询到手机号 ==>> {}".format(res3))
                        if not res2:  # 如果要修改的用户不存在于数据库中，res2为空
                            return jsonify({"code": 4005, "msg": "修改的用户ID不存在，无法进行修改，请检查！！！"})
                        elif res3:  # 如果要修改的手机号已经存在于数据库中，res3非空
                            return jsonify({"code": 4006, "msg": "手机号已被注册，无法进行修改，请检查！！！"})
                        else:
                            # 如果请求参数不传address，那么address字段不会被修改，仍为原值
                            # if not new_address:
                            # new_address = res2[0]["address"]
                            # 把传入的明文密码通过MD5加密变为密文
                            new_password = get_md5(res2[0]["username"], new_password)
                            sql3 = "UPDATE user SET password = '{}', telephone = '{}' " \
                                   "WHERE id = {}".format(new_password, new_telephone, id)
                            db.execute_db(sql3)
                            print("修改用户信息SQL ==>> {}".format(sql3))
                            return jsonify({"code": 0, "msg": "恭喜，修改用户信息成功！"})
                    else:
                        return jsonify({"code": 4004, "msg": "当前用户不是管理员用户，无法进行操作，请检查！！！"})
                else:
                    return jsonify({"code": 4003, "msg": "token口令不正确，请检查！！！"})
            else:
                return jsonify({"code": 4002, "msg": "当前用户未登录，请检查！！！"})
    else:
        return jsonify({"code": 4001, "msg": "管理员用户/token口令/密码/手机号不能为空，请检查！！！"})


@app.route("/delete/user/<string:username>", methods=['POST'])
def user_delete(username):
    """删除用户信息"""
    admin_user = request.values.get("admin_user", "").strip()  # 当前登录的管理员用户
    token = request.values.get("token", "").strip()  # token口令
    if admin_user and token:  # 用户和token口令不为空
        redis_token = redis_db.handle_redis_token(admin_user)  # 从redis中取token
        if redis_token:
            if redis_token == token:  # 如果从redis中取到的token不为空，且等于请求body中的token
                sql1 = "SELECT role FROM user WHERE username = '{}'".format(admin_user)
                res1 = db.select_db(sql1)
                print("根据用户名 【 {} 】 查询到用户类型 == >> {}".format(admin_user, res1))
                user_role = res1[0]["role"]
                if user_role == 0:  # 如果当前登录用户是管理员用户
                    sql2 = "SELECT * FROM user WHERE username = '{}'".format(username)
                    res2 = db.select_db(sql2)
                    print(sql2)
                    print("根据用户名 【 {} 】 查询到用户信息 ==>> {}".format(username, res2))
                    if not res2:  # 如果要删除的用户不存在于数据库中，res2为空
                        return jsonify({"code": 3005, "msg": "删除的用户名不存在，无法进行删除，请检查！！！"})
                    elif res2[0]["role"] == 0:  # 如果要删除的用户是管理员用户，则不允许删除
                        return jsonify({"code": 3006, "msg": "用户名：【 {} 】，该用户不允许删除！！！".format(username)})
                    else:
                        sql3 = "DELETE FROM user WHERE username = '{}'".format(username)
                        db.execute_db(sql3)
                        print("删除用户信息SQL ==>> {}".format(sql3))
                        return jsonify({"code": 0, "msg": "恭喜，删除用户信息成功！"})
                else:
                    return jsonify({"code": 3004, "msg": "当前用户不是管理员用户，无法进行操作，请检查！！！"})
            else:
                return jsonify({"code": 3003, "msg": "token口令不正确，请检查！！！"})
        else:
            return jsonify({"code": 3002, "msg": "当前用户未登录，请检查！！！"})
    else:
        return jsonify({"code": 3001, "msg": "管理员用户/token口令不能为空，请检查！！！"})
