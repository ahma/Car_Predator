# -*- coding: utf-8 -*-
from __future__ import division

__author__ = 'ahma'

import sqlite3
from datetime import datetime
from time import sleep

from bs4 import BeautifulSoup
import requests
import config
import notification

conn = sqlite3.connect('cars.db')

MAIN_URL = 'http://m.hasznaltauto.hu/auto/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.2; Nexus 5 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.99 Mobile Safari/537.36'}


def get_car_info(car_url):
    car_info_dict = {}
    try:
        car_info_call = requests.get(car_url, headers=HEADERS)
        car_info_call_content = car_info_call.text

        parsed_html = BeautifulSoup(car_info_call_content, 'html.parser')

        head = parsed_html.find("div", class_="rounded-box txt").strong.text.encode('utf-8')
        car_info_dict['head'] = head
        car_info_dict['company'] = head.split(' ')[0]
        car_info_dict['model'] = head.split(' ')[1]
        car_info_dict['variant'] = ' '.join(head.split(' ')[2:])

        info = parsed_html.find("div", class_="hirdetes-data").find_all("div")

        for idx, val in enumerate(info):
            try:
                val_clean = val.text.encode('utf-8')
                if val_clean == 'Évjárat:':
                    age = info[idx+1].text.encode('utf-8')
                    car_info_dict['age'] = age
                    if '/' not in age:
                        age = age+'/01'

                    age_date = datetime.strptime(age, '%Y/%m')
                    epoch = int(age_date.strftime('%s'))
                    car_info_dict['epoch'] = epoch

                elif val_clean == 'Kilométeróra állása:':
                    km = int(info[idx+1].text.split('km')[0].replace(" ", ""))
                    car_info_dict['km'] = km
                elif val_clean == 'Hengerűrtartalom:':
                    car_info_dict['ccm'] = int(info[idx+1].text.encode('utf-8').replace(" cm³", ""))
                elif val_clean == 'Teljesítmény:':
                    car_info_dict['hp'] = int(info[idx+1].text.split(',')[1].replace(" LE", ""))
            except Exception as err:
                print car_url
                print err
        epoch_now = int(datetime.now().strftime('%s'))
        car_info_dict['km_year'] = km / ((epoch_now - epoch) / 31536000)
        car_info_dict['parts'] = parsed_html.find_all("div", class_="rounded-box txt")[1].find("div").text.encode('utf-8')
        car_info_dict['other_info'] = parsed_html.find_all("div", class_="rounded-box txt")[2].find("div").text.encode('utf-8')
        car_info_dict['car_description'] = parsed_html.find_all("div", class_="rounded-box txt")[3].find("div").text.encode('utf-8')
    except Exception as err:
        print err
        pass

    return car_info_dict


def check(search_hash):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cars_table (
car_url text, car_title text, car_pic text, car_desc text, car_price text, head text, car_description text, age text,
other_info text, variant text, parts text, km integer, ccm integer, epoch integer, hp integer, km_year integer, model text, company text
)''')


    call = requests.get(MAIN_URL+search_hash, headers=HEADERS)
    call_content = call.text

    parsed_html = BeautifulSoup(call_content, 'html.parser')
    cars = parsed_html.find_all("a", class_="ui-link")

    for car in cars:
        car_url = str(car['href'])
        if len(c.execute("SELECT * FROM cars_table WHERE car_url='%s'" % car_url).fetchall()) != 0:
            continue


        car_title = car.img['alt'].encode('utf-8')
        car_pic = car.img['src'].encode('utf-8')
        car_desc = car.p.text.encode('utf-8')
        car_price = car.strong.text.encode('utf-8')

        res_car_info = get_car_info(car_url)

        c_head = str(res_car_info.get('head', ''))
        c_car_description = str(res_car_info.get('car_description', ''))
        c_age = str(res_car_info.get('age', ''))
        c_other_info = str(res_car_info.get('other_info', ''))
        c_variant = str(res_car_info.get('variant', ''))
        c_parts = str(res_car_info.get('parts', ''))
        c_km = res_car_info.get('km', 0)
        c_ccm = res_car_info.get('ccm', 0)
        c_epoch = res_car_info.get('epoch', 0)
        c_hp = res_car_info.get('hp', 0)
        c_km_year = res_car_info.get('km_year', 0)
        c_model = str(res_car_info.get('model', ''))
        c_company = str(res_car_info.get('company', ''))

        try:
            c.execute("INSERT INTO cars_table VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%d', '%d', '%d', '%d', '%d', '%s', '%s');"
                      % (car_url, car_title, car_pic, car_desc, car_price, c_head, c_car_description, c_age, c_other_info, c_variant, c_parts, c_km, c_ccm, c_epoch, c_hp, c_km_year, c_model, c_company))
        except Exception as err:
            print err

        message = '%s (%s) - %s \n%s \n%s Ekm->%s Ekm/year \n\n%s' \
                  % (c_head, c_age, car_price, car_desc, c_km/1000, c_km_year/1000, car_url)
        if not config.silent_mode:
            notification.pushover(token=config.pushover['token'], api_user=config.pushover['api_user'], message=message)
        print 'New Target!'
        sleep(0.2)


    conn.commit()

targets = config.targets

for target in targets:
    print 'Checking: %s' % target['info']
    check(target['search_hash'])

conn.close()
