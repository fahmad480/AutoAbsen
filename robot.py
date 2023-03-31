import time
# import re
# from os import path, remove
# import schedule
# import sys
from datetime import datetime  # , timedelta
from dhooks import Webhook  # , Embed
# from random import randrange
# import getopt
import requests
# from csv import reader
from lxml import html
from bs4 import BeautifulSoup
import mysql.connector
from cryptography.fernet import Fernet

LOGIN_URL = "https://elearning.itenas.ac.id/login/index.php"

fernet_key = b'yY5oeWM_vgbfnRXHN2y2V6soFh9ciUSwMWUTumgktzM='
fernet = Fernet(fernet_key)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="autoabsen"
)


def headerMaker(referer):
    headers = {
        "referer": referer,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
    }
    return headers


def listToString(s):

    # initialize an empty string
    str1 = " "

    # return string
    return (str1.join(s))


def get_elearning_data(session_requests):
    profilephp = session_requests.get('https://elearning.itenas.ac.id/user/profile.php',
                                      headers=headerMaker('https://elearning.itenas.ac.id/'), allow_redirects=True)
    soup = BeautifulSoup(profilephp.content, 'html.parser')
    name = soup.find('h1').text
    images = soup.find_all("img", class_="userpicture")
    profile_picture = None
    for image in images:
        profile_picture = image['src']
    return name, profile_picture


def joinClass(datas):
    """
    Join Class function, user start login -> go to attendance link -> present
    """
    for account in datas:
        USERNAME = account[0]
        PASSWORD = fernet.decrypt(account[1].encode()).decode()
        DHOOKS = account[2]
        CLASS_NAME = account[3]
        CLASS_URL = account[4]
        CLASS_DAY = account[5]
        CLASS_TIME = account[6]

        send_dhooks = True

        try:
            discord_webhook = Webhook(DHOOKS)
        except:
            send_dhooks = False

        # ---------------------------------------[ DECLARE REQUEST SESSION ]--------------------------------------- #
        session_requests = requests.session()

        # ---------------------------------------[ GET LOGIN TOKEN FROM LOGIN PAGE ]--------------------------------------- #
        loopRes = True
        countLoopRes = 0
        while loopRes is True:
            try:
                result = session_requests.get(LOGIN_URL)
                tree = html.fromstring(result.text)
                authenticity_token = list(
                    set(tree.xpath("//input[@name='logintoken']/@value")))[0]
                loopRes = False
            except:
                countLoopRes += 1
                if countLoopRes >= 10:
                    break
                pass
        if countLoopRes >= 10:
            print(
                "[-] Username %s Gagal akses elearning, \"closed connection\", silahkan absen manual [ERROR1]" % (USERNAME))
            if send_dhooks is True:
                discord_webhook.send(
                    "[-] Username %s Gagal akses elearning, \"closed connection\", silahkan absen manual [ERROR1]" % (USERNAME))
            continue

        # ---------------------------------------[ CREATE LOGIN PAYLOAD ]--------------------------------------- #
        payload = {
            "username": USERNAME,
            "password": PASSWORD,
            "logintoken": authenticity_token
        }

        # ---------------------------------------[ LOGIN ACTION ]--------------------------------------- #
        loopRes = True
        countLoopRes = 0
        while loopRes is True:
            try:
                result = session_requests.post(
                    LOGIN_URL, data=payload, headers=headerMaker(LOGIN_URL))
                loopRes = False
            except:
                countLoopRes += 1
                if countLoopRes >= 10:
                    break
                pass
        if countLoopRes >= 10:
            print(
                "[-] Username %s Gagal akses elearning, \"closed connection\", silahkan absen manual [ERROR2]" % (USERNAME))
            if send_dhooks is True:
                discord_webhook.send(
                    "[-] Username %s Gagal akses elearning, \"closed connection\", silahkan absen manual [ERROR2]" % (USERNAME))
            continue

        # ---------------------------------------[ CHECK IF LOGIN SUCCESS OR NOT ]--------------------------------------- #
        if result.url == LOGIN_URL:
            print(
                "[-] Username %s Gagal login, kemungkinan username atau password salah [ERROR3]" % (USERNAME))
            if send_dhooks is True:
                discord_webhook.send(
                    "[-] Username %s Gagal login, kemungkinan username atau password salah [ERROR3]" % (USERNAME))
            continue
        else:
            # ---------------------------------------[ GET ELEARNING DATA ]--------------------------------------- #

            NAME, profile_picture = get_elearning_data(session_requests)

            # ---------------------------------------[ GET ATTENDANCE URL ]--------------------------------------- #
            print("[+] %s Berhasil login [%s]" % (NAME, result.url))
            loopRes = True
            countLoopRes = 0
            while loopRes is True:
                try:
                    attendance_page = session_requests.get(
                        CLASS_URL, headers=headerMaker(CLASS_URL), allow_redirects=True)
                    soup = BeautifulSoup(
                        attendance_page.content, 'html.parser')
                    subm = soup.findAll('a')
                    attend_link = ''
                    for link in subm:
                        if '/attendance/attendance.php?sessid=' in str(link):
                            attend_link = link
                            print('[+] URL Attendance didapatkan')
                            break
                    loopRes = False
                except:
                    countLoopRes += 1
                    if countLoopRes >= 10:
                        break
                    pass
            if countLoopRes >= 10:
                print('[-] Gagal mendapatkan URL Attendance [ERROR4]')
                if send_dhooks is True:
                    discord_webhook.send(
                        "[-] %s gagal absen otomatis %s, karena link present tidak ada [ERROR4]" % (NAME, CLASS_NAME))
                continue
            # ---------------------------------------[ GET SESSIONS ID AND SESSION KEY ]--------------------------------------- #
            loopRes = True
            countLoopRes = 0
            while loopRes is True:
                try:
                    soup = BeautifulSoup(str(attend_link), 'html.parser')
                    href = soup.find('a')
                    href = str(href['href'])
                    attend_link = href.replace("amp;", "")

                    sesskey = attend_link.split("&")[1].split("=")[1]
                    sessid = attend_link.split("?")[1].split("&")[
                        0].split("=")[1]

                    print('[!] Mendapatkan Session ID dan Key [%s] [%s]' %
                          (sesskey, sessid))
                    loopRes = False
                except:
                    countLoopRes += 1
                    if countLoopRes >= 10:
                        break
                    pass
            if countLoopRes >= 10:
                print(
                    '[-] Gagal Mendapatkan Session ID dan Key [ERROR5]')
                if send_dhooks is True:
                    discord_webhook.send(
                        "[-] %s gagal absen otomatis %s, karena gagal get Session ID dan Key [ERROR5]" % (NAME, CLASS_NAME))
                continue
            # ---------------------------------------[ GET PRESENT RADIO BUTTON VALUE ]--------------------------------------- #
            loopRes = True
            countLoopRes = 0
            while loopRes is True:
                try:
                    attendance_page = session_requests.get(attend_link, headers=headerMaker(
                        CLASS_URL), allow_redirects=True)

                    soup = BeautifulSoup(attendance_page.content, 'lxml')
                    tree = html.fromstring(attendance_page.content)
                    labless = tree.xpath(
                        '/html/body/div[1]/div[3]/div/div/section/div[1]/form/fieldset/div/div/div[2]/label[1]/input/@value')[0]
                    loopRes = False
                except:
                    countLoopRes += 1
                    if countLoopRes >= 10:
                        break
                    pass
            if countLoopRes >= 10:
                print('[-] Gagal mendapatkan value present [ERROR6]')
                if send_dhooks is True:
                    discord_webhook.send(
                        "[-] %s Gagal absen otomatis %s, silahkan absen manual [ERROR6]" % (NAME, CLASS_NAME))
                continue
            # ---------------------------------------[ CREATE PRESENT PAYLOAD ]--------------------------------------- #
            payload = {
                "sessid": sessid,
                "sesskey": sesskey,
                "sesskey": sesskey,
                "_qf__mod_attendance_student_attendance_form": 1,
                "mform_isexpanded_id_session": 1,
                "status": labless,
                "submitbutton": "Save changes"
            }

            # ---------------------------------------[ SEND PRESENT PAYLOAD ]--------------------------------------- #
            loopRes = True
            countLoopRes = 0
            while loopRes is True:
                try:
                    result = session_requests.post(attend_link, data=payload, headers=headerMaker(
                        CLASS_URL), allow_redirects=True)
                    loopRes = False
                except:
                    countLoopRes += 1
                    if countLoopRes >= 10:
                        break
                    pass
            if countLoopRes >= 10:
                print(
                    "[-] %s Gagal akses elearning, \"closed connection\", silahkan absen manual [ERROR7]" % (NAME))
                if send_dhooks is True:
                    discord_webhook.send(
                        "[-] %s Gagal akses elearning, \"closed connection\", silahkan absen manual [ERROR7]" % (NAME))
                continue
            # ---------------------------------------[ CHECK IF PRESENT IS SUCCESS OR NOT ]--------------------------------------- #
            if result.url != attendance_page.url:
                if send_dhooks is True:
                    discord_webhook.send(
                        "[+] %s Berhasil absen mata kuliah '%s'" % (NAME, CLASS_NAME))
                print("[+] Berhasil Absen")
            else:
                if send_dhooks is True:
                    discord_webhook.send(
                        "[-] %s Gagal absen mata kuliah, silahkan absen manual '%s' [ERROR8]" % (NAME, CLASS_NAME))
                print(
                    "[-] %s Gagal absen mata kuliah, silahkan absen manual '%s' [ERROR8]" % (NAME, CLASS_NAME))


def getCollegerData(day, time):
    cursor = db.cursor()
    sql = """SELECT a.username, a.password, a.dhooks, c.name AS class_name, c.url AS class_url, c.day AS class_day, c.time AS class_time FROM account AS a
    INNER JOIN account_class AS ac ON ac.username_account = a.username
    INNER JOIN class AS c ON c.id = ac.id_class AND c.day = '%s' AND c.time = '%s'
    """ % (day, time)
    cursor.execute(sql)
    results = cursor.fetchall()
    print(len(results))
    return results


def startTukangAbsen():
    while True:
        now = datetime.now()
        current_time = now.strftime("%M:%S")
        current_hour = now.strftime("%H:00")
        current_day = now.strftime("%A")
        if current_day == "Monday":
            current_day = "senin"
        elif current_day == "Tuesday":
            current_day = "selasa"
        elif current_day == "Wednesday":
            current_day = "rabu"
        elif current_day == "Thursday":
            current_day = "kamis"
        elif current_day == "Friday":
            current_day = "jumat"
        elif current_day == "Saturday":
            current_day = "sabtu"
        elif current_day == "Sunday":
            current_day = "minggu"

        if current_time == "00:01":
            print("Tukang Absen Menjalankan Robot")
            result = getCollegerData(current_day, current_hour)
            joinClass(result)
        time.sleep(1)


if __name__ == '__main__':
    print("Tukang Absen Dijalankan")
    startTukangAbsen()
