import time
import re
from os import path, remove
import schedule
import sys
from datetime import datetime, timedelta
from dhooks import Webhook, Embed
from random import randrange
import getopt
import requests
from csv import reader
from lxml import html
from bs4 import BeautifulSoup

LOGIN_URL = "https://elearning.itenas.ac.id/login/index.php"
# discord_webhook = Webhook(
#     'https://discord.com/api/webhooks/776949064163524610/OSlekPPTKpnocIzTcITgho8vItIQlbk64_qfFSttdR2eUEvShWIAZPyZyMEcryitI14-')
discord_webhook = Webhook(
    'https://discord.com/api/webhooks/780210384463724604/CrWicY_lpzeKxoTtuKbKLcHH3GTr5qvdXGId-cCYOZdHz0ff9fdJsTfMaQ_fu_UTfbqO')


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


def joinClass(Schedule):
    """
    Join Class function, user start login -> go to attendance link -> present
    """
    course_name = Schedule[0]
    course_attendance_links = Schedule[1]
    course_day = Schedule[2]
    course_start_time = Schedule[3]
    course_link = Schedule[2]

    failedList = []

    with open('Account.csv', encoding="utf-8") as csvfile:
        accReader = reader(csvfile)
        now = datetime.now()

        for account in accReader:
            USERNAME = account[0]
            PASSWORD = account[1]
            NAME = account[2]

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
                    "[-] %s Gagal akses elearning, closed connection, silahkan absen manual [ERROR1]" % (NAME))
                discord_webhook.send(
                    "[-] %s Gagal akses elearning, closed connection, silahkan absen manual [ERROR1]" % (NAME))
                failedList.append(NAME)
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
                    "[-] %s Gagal akses elearning, closed connection, silahkan absen manual [ERROR2]" % (NAME))
                discord_webhook.send(
                    "[-] %s Gagal akses elearning, closed connection, silahkan absen manual [ERROR2]" % (NAME))
                failedList.append(NAME)
                continue

            # ---------------------------------------[ CHECK IF LOGIN SUCCESS OR NOT ]--------------------------------------- #
            if result.url == LOGIN_URL:
                discord_webhook.send(
                    "[-] %s Gagal login, silahkan absen manual [ERROR3]" % (NAME))
                print("[-] %s Gagal login, silahkan absen manual [ERROR3]" % (NAME))
                failedList.append(NAME)
                continue
            else:
                # ---------------------------------------[ GET ATTENDANCE URL ]--------------------------------------- #
                print("[+] %s Berhasil login [%s]" % (NAME, result.url))
                loopRes = True
                countLoopRes = 0
                while loopRes is True:
                    try:
                        attendance_page = session_requests.get(
                            course_attendance_links, headers=headerMaker(course_link), allow_redirects=True)
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
                    discord_webhook.send(
                        "[-] %s gagal absen otomatis %s, karena link present tidak ada [ERROR4]" % (NAME, course_name))
                    failedList.append(NAME)
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
                    discord_webhook.send(
                        "[-] %s gagal absen otomatis %s, karena gagal get Session ID dan Key [ERROR5]" % (NAME, course_name))
                    failedList.append(NAME)
                    continue
                # ---------------------------------------[ GET PRESENT RADIO BUTTON VALUE ]--------------------------------------- #
                loopRes = True
                countLoopRes = 0
                while loopRes is True:
                    try:
                        attendance_page = session_requests.get(attend_link, headers=headerMaker(
                            course_attendance_links), allow_redirects=True)

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
                    discord_webhook.send(
                        "[-] %s Gagal absen otomatis %s, silahkan absen manual [ERROR6]" % (NAME, course_name))
                    failedList.append(NAME)
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
                            course_attendance_links), allow_redirects=True)
                        loopRes = False
                    except:
                        countLoopRes += 1
                        if countLoopRes >= 10:
                            break
                        pass
                if countLoopRes >= 10:
                    print(
                        "[-] %s Gagal akses elearning, closed connection, silahkan absen manual [ERROR7]" % (NAME))
                    discord_webhook.send(
                        "[-] %s Gagal akses elearning, closed connection, silahkan absen manual [ERROR7]" % (NAME))
                    failedList.append(NAME)
                    continue
                # ---------------------------------------[ CHECK IF PRESENT IS SUCCESS OR NOT ]--------------------------------------- #
                if result.url != attendance_page.url:
                    discord_webhook.send(
                        "[+] %s Berhasil absen mata kuliah '%s'" % (NAME, course_name))
                    print("[+] Berhasil Absen")
                else:
                    discord_webhook.send(
                        "[-] %s Gagal absen mata kuliah, silahkan absen manual '%s' [ERROR8]" % (NAME, course_name))
                    print(
                        "[-] %s Gagal absen mata kuliah, silahkan absen manual '%s' [ERROR8]" % (NAME, course_name))
                    failedList.append(NAME)
        try:
            f = open("kannalist.txt", "r").read().splitlines()
            image = f[randrange(len(f))]
            embed = Embed(
                color=0x5CDBF0,
            )
            embed.set_image(image)
            footer = 'buah: ' + listToString(failedList)
            embed.set_footer(text=footer)
            discord_webhook.send(embed=embed)
        except:
            print('[-] Gagal kirim gambar [ERROR9]')


def sched():
    """
    Start import schedule
    """
    with open('Schedule.csv', encoding="utf-8") as csvfile:
        schedReader = reader(csvfile)
        now = datetime.now()

        for Schedule in schedReader:
            name = Schedule[0]
            links = Schedule[1]
            day = Schedule[2]
            start_time = Schedule[3]

            if day.lower() == "senin":
                schedule.every().monday.at(start_time).do(joinClass, Schedule)
                print("[#] Berhasil memasukan kelas '%s' ke jadwal otomatis di hari %s jam %s" %
                      (name, day, start_time))
            if day.lower() == "selasa":
                schedule.every().tuesday.at(start_time).do(joinClass, Schedule)
                print("[#] Berhasil memasukan kelas '%s' ke jadwal otomatis di hari %s jam %s" %
                      (name, day, start_time))
            if day.lower() == "rabu":
                schedule.every().wednesday.at(start_time).do(joinClass, Schedule)
                print("[#] Berhasil memasukan kelas '%s' ke jadwal otomatis di hari %s jam %s" %
                      (name, day, start_time))
            if day.lower() == "kamis":
                schedule.every().thursday.at(start_time).do(joinClass, Schedule)
                print("[#] Berhasil memasukan kelas '%s' ke jadwal otomatis di hari %s jam %s" %
                      (name, day, start_time))
            if day.lower() == "jumat":
                schedule.every().friday.at(start_time).do(joinClass, Schedule)
                print("[#] Berhasil memasukan kelas '%s' ke jadwal otomatis di hari %s jam %s" %
                      (name, day, start_time))
            if day.lower() == "sabtu":
                schedule.every().saturday.at(start_time).do(joinClass, Schedule)
                print("[#] Berhasil memasukan kelas '%s' ke jadwal otomatis di hari %s jam %s" %
                      (name, day, start_time))
            if day.lower() == "minggu":
                schedule.every().sunday.at(start_time).do(joinClass, Schedule)
                print("[#] Berhasil memasukan kelas '%s' ke jadwal otomatis di hari %s jam %s" %
                      (name, day, start_time))
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    discord_webhook.send(
        "[!] Bot (v2) Mulai Berjalan")
    sched()
