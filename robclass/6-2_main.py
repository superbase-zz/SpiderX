import re
from bs4 import BeautifulSoup
import time
from selenium.webdriver import Chrome
import json
import requests
from selenium.webdriver.chrome.options import Options

from chaojiying import Chaojiying_Client
chaojiying = Chaojiying_Client('wscjxky', 'wscjxky123', '898146')  # 用户中心>>软件ID 生成一个替换 96001
from config import FateadmApi, robclass_headers, headers, headers_image, check_classheader


pd_id = "103797"
pd_key = "L5oPz3M0cbHJhiOfzs1gTk4oW9b2yVsB"
app_id = "303997"  # 开发者分成用的账号，在开发者中心可以查询到
app_key = "o8SL2OUcncoCeYCDuN7PhS/54Ns/wepQ"
pred_type = "40300"
api = FateadmApi(app_id, app_key, pd_id, pd_key)


def get_Session():
    BCOOKIES = {}
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('disable-infobars')
    driver = Chrome(executable_path='chromedriver.exe',
                    options=chrome_options)
    url = 'https://mis.bjtu.edu.cn/home/'
    driver.get(url)
    driver.maximize_window()
    elem = driver.find_element_by_css_selector('#id_loginname')
    elem.send_keys(username)
    elem = driver.find_element_by_xpath('//*[@id="id_password"]')
    elem.send_keys(password)
    elem = driver.find_element_by_xpath('//*[@id="form1"]/div/div/button')
    elem.click()
    elem = driver.find_element_by_xpath(
        '//*[@id="wrap"]/div[2]/div[2]/div/div[2]/div/div/table/tbody/tr[1]/td[6]/div/div/h5/a')
    elem.click()
    time.sleep(1)
    handles = driver.window_handles
    driver.switch_to.window(handles[-1])
    cookie = driver.get_cookies()
    while len(cookie) <= 1:
        get_Session()
    for i in cookie:  # 添加cookie到CookieJar
        BCOOKIES[i["name"]] = i["value"]
    print('reload' + str(BCOOKIES))

    ssrequest = requests.session()
    requests.utils.add_dict_to_cookiejar(ssrequest.cookies, BCOOKIES)
    driver.close()
    driver.quit()
    return ssrequest.cookies


# from requests_html import HTMLSession


def post_request(cookies, class_code, hashkey, answer, req_id, pred_type='pp', count=0):
    while count < 50:
        check_url = 'https://dean.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?action=load&iframe=school&page=1&perpage=500'
        res = requests.get(check_url, cookies=cookies, headers=check_classheader)
        count += 1
    data = {'checkboxs': class_code,
            'hashkey': hashkey,
            'answer': answer
            }
    re = requests.post('https://dean.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?action=submit',
                       cookies=cookies,
                       headers=robclass_headers,
                       allow_redirects=False,
                       data=data)
    if re.status_code == 503:
        print(re.status_code)
        print("重新提交抢课请求")
        time.sleep(0.5)
        post_request(cookies, class_code, hashkey, answer, req_id, pred_type, 50)
    re = re.headers['Set-Cookie']
    message = re[re.find('[['):re.find(']]') + 2]
    res = str(json.loads(eval("'" + message + "'")))
    print(res)
    if "选课成功" in res:
        return 200
    elif "课堂无课余量" in res:
        return 404
    elif "验证码" in res:
        if pred_type == 'pp':
            api.Justice(req_id)
        else:
            chaojiying.ReportError(req_id)
        return 403
    else:
        return 500


def has_free(kecheng_code, xuhao, pred_type='pp'):
    global cookies
    check_url = 'https://dean.bjtu.edu.cn/course_selection/courseselecttask/selects_action/?action=load&iframe=school&page=1&perpage=500'
    # sess=HTMLSession()
    # res=sess.get(check_url, cookies=cookies, headers=check_classheader)
    # print(res.text)
    res = requests.get(check_url, cookies=cookies, headers=check_classheader)
    soup = BeautifulSoup(res.text, 'html.parser')
    table = soup.find('div', id='current')
    if table:
        class_trs = table.find_all('tr')[1:]
        for tr in class_trs:
            if kecheng_code in tr.text:
                has_free = tr.find('input')
                if has_free:
                    class_code = has_free["value"].strip()
                    class_name = tr.find('div', class_='hide').text.strip()
                    class_name = re.search("】(.*)", class_name).group(1)
                    if xuhao in class_name:
                        print("有课余量：")
                        print(class_name)
                        print(class_code)
                        res = requests.get('https://dean.bjtu.edu.cn/captcha/refresh/', cookies=cookies,
                                           headers=headers_image)
                        json_data = res.json()
                        hashkey = json_data['key']
                        print(json_data)
                        img_data = requests.get('https://dean.bjtu.edu.cn' + json_data['image_url'], headers=headers)
                        if pred_type == 'pp':
                            pred_type = 'pp'
                            answer, req_id = api.Predict(40300, img_data.content)
                        else:
                            pred_type = 'cjy'
                            answer, req_id = chaojiying.PostPic(img_data.content, 2003)
                        result = post_request(cookies=cookies, class_code=class_code, hashkey=hashkey, answer=answer,
                                              req_id=req_id, pred_type=pred_type)
                        if result == 200:
                            return True
    return False


if __name__ == '__main__':
    with open('rob_data.txt', 'r')as f:
        ls = f.readlines()
        for line in ls:
            line = line.strip('\n')
            data = line.split(' ')
            username = data[0]
            password = data[1]
            kecheng_code = data[2].split(',')
            xuhao = data[3].split(',')
    print(username, password, kecheng_code, xuhao)
    # username = '18251076'
    # password = '10962905'
    # kecheng_code = ['85L074T']
    # xuhao = ["11"]
    time_delay = 0.1
    retry_max = 50000
    reset = False
    i = 0
    retry_num = 0
    cookies = get_Session()
    while True:
        try:
            if retry_num > retry_max:
                reset = True
                retry_num = 0
                # cookies = get_Session()
                continue
            if i == len(kecheng_code):
                i = 0
            if has_free(kecheng_code=kecheng_code[i], xuhao=xuhao[i], pred_type='cjy'):
                print(username, password)
                print("搶課完成" + str(kecheng_code[i]))
                break
            else:
                if retry_num % 200 == 0:
                    print('retry_time : ' + str(retry_num))
                i += 1
                retry_num += 1
                reset = False
        except Exception as e:
            print(e)
            continue
