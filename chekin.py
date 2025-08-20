import requests
from lxml import etree
import os

# --- 配置参数 ---
login_url = "https://vip.ioshashiqi.com/aspx3/mobile/login.aspx"
qiandao_url = "https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx?action=list&s=&no="
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

# 从环境变量中获取用户名和密码 (适用于 GitHub Actions Secrets)
USERNAME = os.environ.get('HASHIQI_USERNAME', '')
PASSWORD = os.environ.get('HASHIQI_PASSWORD', '')

# 如果敏感信息缺失，程序直接退出 (本地测试时可暂时注释，或设置环境变量)
if not USERNAME or not PASSWORD:
    print("错误：无法获取用户名或密码。请确保已在 GitHub Secrets 中设置 'IOSHASHIQI_USERNAME' 和 'IOSHASHIQI_PASSWORD'，或在本地设置环境变量。")
    exit(1)

# 通用请求头
common_headers = {
    "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "User-Agent": user_agent,
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

session = requests.Session() # 使用 Session 保持会话和 Cookies

# 定义一个辅助函数，安全地获取XPath结果 (防止 IndexError)
def get_xpath_value(parser, xpath_str, default=''):
    result = parser.xpath(xpath_str)
    return result[0] if result else default

# ================== 第一步：执行登录操作 (与之前相同) ==================
print("--- 执行登录操作 ---")
login_page_response = session.get(login_url, headers=common_headers)
login_page_parser = etree.HTML(login_page_response.text)

viewstate_login = get_xpath_value(login_page_parser, '//input[@name="__VIEWSTATE"]/@value')
eventvalidation_login = get_xpath_value(login_page_parser, '//input[@name="__EVENTVALIDATION"]/@value') # 登录页面可能需要
user_name_attr = get_xpath_value(login_page_parser, '//*[@id="txtUser_sign_in"]/@name', 'txtUser_sign_in')
pass_name_attr = get_xpath_value(login_page_parser, '//*[@id="txtPwd_sign_in"]/@name', 'txtPwd_sign_in')
login_button_name = get_xpath_value(login_page_parser, '//input[@type="submit" and @value="登 录"]/@name', 'btnLogin')
login_button_value = get_xpath_value(login_page_parser, f'//input[@name="{login_button_name}"]/@value', '登 录')

login_post_data = {
    "__VIEWSTATE": viewstate_login,
    "__EVENTVALIDATION": eventvalidation_login, # 登录页面可能需要
    user_name_attr: USERNAME,
    pass_name_attr: PASSWORD,
    login_button_name: login_button_value,
}

login_post_headers = {
    **common_headers,
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": login_url
}

login_result_response = session.post(login_url, headers=login_post_headers, data=login_post_data, allow_redirects=False)

if login_result_response.status_code == 302 and 'location' in login_result_response.headers:
    print(f"登录成功！重定向至: {login_result_response.headers['location']}")
else:
    print("登录可能失败，请检查用户名、密码或表单提交参数。")
    print("登录响应状态码:", login_result_response.status_code)
    print("登录响应内容 (部分):", login_result_response.text[:500])
    exit("登录失败，程序终止。")


# ================== 第二步：访问签到页面并模拟点击签到按钮 ==================
print("\n--- 访问签到页面并模拟点击签到 ---")

# 2.1 获取签到页面 (GET请求)
qiandao_page_response = session.get(qiandao_url, headers=common_headers)
qiandao_page_parser = etree.HTML(qiandao_page_response.text)

# 2.2 【关键修改】从签到页面提取 Postback 所需的隐藏字段
qiandao_viewstate = get_xpath_value(qiandao_page_parser, '//input[@name="__VIEWSTATE"]/@value')
qiandao_viewstategenerator = get_xpath_value(qiandao_page_parser, '//input[@name="__VIEWSTATEGENERATOR"]/@value')

# 根据HTML分析，签到按钮触发的 Postback 是 __doPostBack("_lbtqd", "")
event_target = "_lbtqd"
event_argument = ""

print(f"签到页面 __VIEWSTATE: {qiandao_viewstate[:30]}...")
print(f"签到页面 __VIEWSTATEGENERATOR: {qiandao_viewstategenerator}")


# 2.3 【关键修改】构建点击签到按钮的 POST 数据
# 按照 __doPostBack 机制和 HTML 中发现的隐藏字段来构造
qiandao_post_data = {
    "__EVENTTARGET": event_target,     # 触发 Postback 的控件 ID
    "__EVENTARGUMENT": event_argument, # 随 Postback 传递的参数
    "__VIEWSTATE": qiandao_viewstate,
    "__VIEWSTATEGENERATOR": qiandao_viewstategenerator,
    # 注意：根据提供的HTML，签到页面没有 __EVENTVALIDATION，所以不提交
    # 如果页面有其他隐藏字段，如 txtSomeField="", 也需要添加到这里
}

# 2.4 设置 POST 请求头 (referer指向当前页面)
qiandao_post_headers = {
    **common_headers,
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": qiandao_url # 模拟从签到页面提交
}

# 2.5 发送点击签到按钮的 POST 请求
qiandao_result_response = session.post(qiandao_url, headers=qiandao_post_headers, data=qiandao_post_data, allow_redirects=True)

print("\n--- 点击签到按钮后的页面内容 ---")
# 打印签到后的页面内容，检查是否出现“签到成功”、“您已签到”之类的文字
print(qiandao_result_response.text[:1000])

# 检查签到是否成功
if "签到成功" in qiandao_result_response.text or "您已签到" in qiandao_result_response.text:
    print("\n>>> 自动签到可能成功！ <<<")
else:
    print("\n>>> 自动签到结果待确认，请手动检查页面内容或使用 Burp Suite 抓包调试。 <<<")