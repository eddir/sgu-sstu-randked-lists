from bs4 import BeautifulSoup
import telegram
import requests
import math
import yaml
import sys
import re
import os

config = {
    'token': "",
    'chat': -2,
    'faculties': [
        {
            'url': "https://www.sgu.ru/svodka/mehaniko-matematicheskii_fakultet/prikladnaya_informatika_09.03.03/ochnaya/prikladnaya_informatika_ochnaya_buidzhet_00031",
            'name': "МехМат",
            'user_name': "Ростков Эдуард Александрович",
            'parser': 'sgu',
            'vacancies': 32,
            'passing_score': 167
        },
        {
            'url': "https://www.sgu.ru/svodka/fakultet_kniit/matematicheskoe_obespechenie_i_administrirovanie_informacionnjh_sistem_02.03.03/ochnaya/matematicheskoe_obespechenie_i_administrirovanie_informacionnjh_sistem_ochnaya_buidzhet_00105",
            'name': "КНиИТ_МОиАИС",
            'user_name': "Ростков Эдуард Александрович",
            'parser': 'sgu',
            'vacancies': 23,
            'passing_score': 225
        },
        {
            'url': "https://www.sgu.ru/svodka/fakultet_kniit/fundamentalnaya_informatika_i_informacionnje_tehnologii_02.03.02/ochnaya/fundamentalnaya_informatika_i_informacionnje_tehnologii_ochnaya_buidzhet_00101",
            'name': "КНиИТ_ФИиИТ",
            'user_name': "Ростков Эдуард Александрович",
            'parser': 'sgu',
            'vacancies': 19,
            'passing_score': 223
        },
        {
            'url': "http://pk-info.sstu.ru/AlphabeticalList.aspx?base_id=1&educationForm_id=1&abitType_id=1&spec_id=1530&is_on_category=1",
            'name': "ИнПИТ_ИФСТ",
            'user_name': "Ростков Эдуард Александрович",
            'parser': 'sgtu',
            'vacancies': 31,
            'passing_score': 218
        },
        {
            'url': "http://pk-info.sstu.ru/AlphabeticalList.aspx?base_id=1&educationForm_id=1&abitType_id=1&spec_id=1532&is_on_category=1",
            'name': "ИнПИТ_ПИНФ",
            'user_name': "Ростков Эдуард Александрович",
            'parser': 'sgtu',
            'vacancies': 13,
            'passing_score': 211
        },
        {
            'url': "http://pk-info.sstu.ru/AlphabeticalList.aspx?base_id=1&educationForm_id=1&abitType_id=1&spec_id=1533&is_on_category=1",
            'name': "ИнПИТ_ПИНЖ",
            'user_name': "Ростков Эдуард Александрович",
            'parser': 'sgtu',
            'vacancies': 15,
            'passing_score': 204
        },
    ]
}

config_test = {
    'chat': -1
}


def find_me(rows, my_name):
    for c in rows:
        if my_name in c['name']:
            return c


def send_message(message):
    bot.send_message(chat_id=config['chat'], text=message, parse_mode="Markdown")


def parse_sgu(faculty, my_name):
    text = requests.get(faculty['url']).text
    soup = BeautifulSoup(text, 'html.parser')
    table = soup.findAll('div', {'class': 'over'})[1].findAll('tr')[2:-1]
    table_data = []

    for column in table:
        column_data = column.findAll('td')
        table_data.append({
            'position': column_data[0].text,
            'name': column_data[1].text,
            'score': column_data[2].text,
            'docs': column_data[7].text
        })

    try:
        with open(path + faculty['name'] + ".yml", 'r') as stream:
            last_table_data = yaml.safe_load(stream)
    except OSError:
        with open(path + faculty['name'] + '.yml', 'w') as outfile:
            yaml.dump(table_data, outfile, default_flow_style=False)
        return False

    current = find_me(table_data, my_name)
    last = find_me(last_table_data, my_name)

    if current['position'] != last['position']:
        if current['position'] < last['position']:
            message = "*Рост "
        else:
            message = "*Падение "

        message += faculty['name'] + "*\n\nПредыдущее: `" + last['position'] + "`\nТекущее: `" + current['position'] + "`"
        send_message(message)

    table_docs_data = []
    all_table_docs_data = []
    for column in table_data:
        if 'Оригинал' in column['docs']:
            all_table_docs_data.append(column)
            if column['score'].isdigit() and (column['score'] >= current['score']):
                table_docs_data.append(column)

    table_last_docs_data = []
    for column in last_table_data:
        if not column['score'].isdigit() or column['score'] < current['score']:
            break
        if 'Оригинал' in column['docs']:
            table_last_docs_data.append(column)

    if len(table_docs_data) != len(table_last_docs_data):
        if len(table_docs_data) < len(table_last_docs_data):
            message = "*Рост среди тех, кто принёс оригинал на "
        else:
            message = "*Падение среди тех, кто принёс оригинал на "

        message += faculty['name'] + "*\n\nПредыдущее: `" + str(len(table_last_docs_data)) + "`\nТекущее: `" + str(
            len(table_docs_data)) + "`"
        send_message(message)

    with open(path + faculty['name'] + '.yml', 'w') as outfile:
        yaml.dump(table_data, outfile, default_flow_style=False)

    current['docs'] = len(table_docs_data)

    if current['docs'] >= faculty['vacancies']:
        current['passing_score'] = table_docs_data[faculty['vacancies'] - 1]['score']
    else:
        if len(all_table_docs_data) >= faculty['vacancies']:
            current['passing_score'] = all_table_docs_data[faculty['vacancies'] - 1]['score']
        else:
            current['passing_score'] = 0

    return current


def parse_sgtu(faculty, my_name):
    text = requests.get(faculty['url']).text
    soup = BeautifulSoup(text, 'html.parser')
    dirty_columns = soup.findAll('tr')
    table = []
    start_save = False
    k = 0

    while not start_save:
        if dirty_columns[k].find('td').text == "Основание приема: Основные конкурсные места ":
            start_save = True
        k += 1

    while start_save:
        if dirty_columns[k].find('td').text != "Основание приема: Выбывшие с конкурса на данное направление ":
            table.append(dirty_columns[k])
            k += 1
        else:
            start_save = False

    table_data = []
    for column in table:
        column_data = column.findAll('td')
        name = re.sub(r'\s+', ' ', column_data[2].text)[1:] #Love Python
        if "1" not in column_data[2].text or my_name in name:
            table_data.append({
                'position': column_data[0].text,
                'name': name,
                'score': column_data[4].text,
                'docs': column_data[3].text
            })

    try:
        with open(path + faculty['name'] + ".yml", 'r') as stream:
            last_table_data = yaml.safe_load(stream)
    except OSError:
        with open(path + faculty['name'] + '.yml', 'w') as outfile:
            yaml.dump(table_data, outfile, default_flow_style=False)
        return False

    current = find_me(table_data, my_name)
    last = find_me(last_table_data, my_name)

    if current['position'] != last['position']:
        if current['position'] < last['position']:
            message = "*Рост "
        else:
            message = "*Падение "

        message += faculty['name'] + "*\n\nПредыдущее: `" + last['position'] + "`\nТекущее: `" + current['position'] + "`"
        send_message(message)

    table_docs_data = []
    all_table_docs_data = []
    for column in table_data:
        if 'оригинал' in column['docs']:
            all_table_docs_data.append(column)
            if column['score'] >= current['score']:
                table_docs_data.append(column)

    table_last_docs_data = []
    for column in last_table_data:
        if column['score'] < current['score']:
            break
        if 'оригинал' in column['docs']:
            table_last_docs_data.append(column)

    if len(table_docs_data) != len(table_last_docs_data):
        if len(table_docs_data) < len(table_last_docs_data):
            message = "*Рост среди тех, кто принёс оригинал на "
        else:
            message = "*Падение среди тех, кто принёс оригинал на "

        message += faculty['name'] + "*\n\nПредыдущее: `" + str(len(table_last_docs_data)) + "`\nТекущее: `" + str(len(table_docs_data)) + "`"
        send_message(message)

    with open(path + faculty['name'] + '.yml', 'w') as outfile:
        yaml.dump(table_data, outfile, default_flow_style=False)

    current['docs'] = len(table_docs_data)

    if current['docs'] >= faculty['vacancies']:
        current['passing_score'] = table_docs_data[faculty['vacancies'] - 1]['score']
    else:
        if len(all_table_docs_data) >= faculty['vacancies']:
            current['passing_score'] = all_table_docs_data[faculty['vacancies'] - 1]['score']
        else:
            current['passing_score'] = 0

    return current

alert = False

if len(sys.argv) > 1:
    if "test" in sys.argv:
        config = {**config, **config_test}
    if "alert" in sys.argv:
        alert = True

path = os.path.dirname(os.path.realpath(__file__)) + "/"
bot = telegram.Bot(token=config['token'])

report = ""

for f in config['faculties']:
    response = False
    if f['parser'] == 'sgu':
        response = parse_sgu(f, f['user_name'])
    if f['parser'] == 'sgtu':
        response = parse_sgtu(f, f['user_name'])

    if response and report is not False:
        report += "[" + f['name'] + "](" + f['url'] + ")\n\n"
        
        first_wave = math.ceil(f['vacancies'] * 0.8)

        if response['docs'] <= f['vacancies']:
            if response['docs'] <= first_wave:
                report += "Зачисление: *в первую волну*\n"
            else:
                report += "Зачисление: *во вторую волну*\n"
        else:
            report += "Зачисление: _нет_\n"
        
        report += "Общий зачёт: `" + response['position'] + "/" + str(f['vacancies']) + " (" + str(first_wave) + ")" + "`\nС аттестатами: `" + str(response['docs']) + "`\nПроходной балл: `"+ str(response['passing_score']) + "/" + str(f['passing_score']) + "`\n\n"
    else:
        report = False

if alert:
    if not report:
        report = "Нет данных для отображения"
    send_message(report)

