import requests
import time
from datetime import datetime
import telebot
from telebot import apihelper
from emoji import emojize
from xml.etree import ElementTree as ET
import numpy as np
import os


def check_data(word):
    with open("cities.txt", "r") as f:
        data = []
        for i in f:
            data.append(i.strip("\n"))
        if word.upper() in data:
            return word
        else:
            return 0


def process_data(word, result):
    a = result.text
    data = []
    prices = []

    root = ET.fromstring(a)
    for child in root.findall('.//result'):
        street = child.find(".//street").text
        price = child.find(".//amount").text
        link = child.find(".//homedetails").text
        row = []
        if price is not None and street is not None and link is not None:
            row.append(street)
            row.append(int(price))
            row.append(link)
            prices.append(int(price))
            data.append(row)

    # find the closest value in array to given input value
    array = np.asarray(prices)
    idx = (np.abs(array - int(word))).argmin()
    price = str(array[idx])

    for i in range(0, len(data)):
        if data[i][1] == int(price):
            street = data[i][0]
            link = data[i][2]
            break

    # to make the price more user-friendly for client
    if len(price) == 5:
        price = price[0:2] + " " + price[2:5]
    elif len(price) == 6:
        price = price[0:3] + " " + price[3:6]
    elif len(price) == 7:
        price = price[0] + " " + price[1:4] + " " + price[4:7]

    return link, street, price


def weather_process(city):
    city = city + ", US"
    city_id = 0
    appid = os.getenv("open_weather_token")
    try:
        p = {'q': city, 'type': 'like', 'units': 'metric', 'APPID': appid}
        URL = "http://api.openweathermap.org/data/2.5/find"
        res = requests.get(URL, params=p)
        data = res.json()
        city_id = data['list'][0]['id']
    except Exception as e:
        print("Exception (find):", e)
        pass
    try:
        p = {'id': city_id, 'units': 'metric', 'lang': 'eng', 'APPID': appid}
        URL = "http://api.openweathermap.org/data/2.5/forecast"
        res = requests.get(URL, params=p)
        data = res.json()
        current_date = time.strftime("%Y-%m-%d", time.gmtime()) # get today date, e.g. 2020-10-25
        weather_forecast = [[current_date]]
        row = []
        closest_forecast = True  # flag to get values from first appearing date in list
        for value in data["list"]:
            # update row to append in a list with every new date
            if value["dt_txt"].split(" ")[0] != weather_forecast[len(weather_forecast)-1][0]:
                row = []

            # add values of the closest date in the list
            if value["dt_txt"].split(" ")[0] == current_date and closest_forecast:    
                closest_forecast = False
                current_weather = weather_forecast[0]
                current_weather.append(str(round(value["main"]["temp"])))
                current_weather.append(value["weather"][0]["description"])

            # night time equals 12, because the US has -7 hours time
            if value["dt_txt"].split(" ")[1] == "12:00:00" and value["dt_txt"].split(" ")[0] != current_date:
                row.append(value["dt_txt"].split(" ")[0])
                row.append(str(round(value["main"]["temp"])))
                weather_forecast.append(row)

            # day time equals 21:00, because the US has -7 hours time
            if value["dt_txt"].split(" ")[1] == "21:00:00" and value["dt_txt"].split(" ")[0] != current_date:
                row.append(str(round(value["main"]["temp"])))
                row.append(value["weather"][0]["description"])
        
        return weather_forecast[0], weather_forecast[1:4]
    except Exception as e:
        print("Exception (forecast):", e)
        pass


def emoji_process(condition):
    # get value from the key in emoji dictionary
    dict = {}
    with open("emoji.txt", "r") as f:
        line = f.readline()
        while len(line) > 1:
            line = line.strip("\n")
            parts = line.split(", ")
            dict[parts[0]] = parts[1]
            line = f.readline()
    return dict[condition]


def output_process(message, current_weather,forecast_weather):
    reserve_emoji_code = ":cloud:" # use this code when no emojis are found
    emoji_code = emoji_process(current_weather[2]) # get emoji code from dictionary
    if emoji_code is None:
        emoji_code = reserve_emoji_code
    if int(current_weather[1]) > 0:
            current_weather[1] = "+" + current_weather[1] # add plus sign to positive temp
    bot.send_message(message.from_user.id, emojize("Now " + current_weather[1] + " " + emoji_code, use_aliases=True))

    for day_forecast in range(0, len(forecast_weather)):
        if day_forecast == 0:
            forecast_weather[day_forecast][0] = "Tomorrow" # replace date with "Tomorrow"
        if day_forecast > 0:
            current_date = time.strftime("%d-%m-%y", time.gmtime()) # get date in the format, e.g. 10-10-2020; UTC current time
            digit_time = time.mktime(time.strptime(current_date, "%d-%m-%y")) + (86400 * (day_forecast+1)) # convert date to digital representation in seconds and add seconds to next day after tomorrow
            forecast_weather[day_forecast][0] = datetime.fromtimestamp(digit_time).strftime("%a") # get day of the week based on digit time

        if int(forecast_weather[day_forecast][1]) > 0:
            forecast_weather[day_forecast][1] = "+" + forecast_weather[day_forecast][1] # add plus sign to positive temp
        if int(forecast_weather[day_forecast][2]) > 0:
            forecast_weather[day_forecast][2] = "+" + forecast_weather[day_forecast][2] # add plus sign to positive temp

        string = forecast_weather[day_forecast][0] + " " + forecast_weather[day_forecast][1] + " " + forecast_weather[day_forecast][2]
        emoji_code = emoji_process(forecast_weather[day_forecast][3])  # get emoji code from dictionary
        if emoji_code is None:
            emoji_code = reserve_emoji_code
        bot.send_message(message.from_user.id, emojize(string + " " + emoji_code, use_aliases=True))
    return None

tg_token = os.getenv("tg_token")
bot = telebot.TeleBot(tg_token)

@bot.message_handler(content_types=['text'])
def start(message):
    word = message.text
    if word == "/start":
        bot.send_message(message.from_user.id, "Hello, write a city where you want to buy a house in the US")
    else:
        city = check_data(word)
        if city == 0:
            bot.send_message(message.from_user.id, "We're sorry, we don't provide our service for this place")
        else:
            bot.send_message(message.from_user.id, "Write the appropriate price: ")
            zillow_token = os.getenv("zillow_token")
            URL = ('http://www.zillow.com/webservice/GetSearchResults.htm?' + zillow_token + '&address=street&citystatezip=' + str(word))
            result = requests.get(URL)
            bot.register_next_step_handler(message, price, result, city)


def price(message, result, city):
    try:
        word = message.text
        word = int(word.replace(" ", ""))
        if 10000 < word < 25000000:
                link, street, number = process_data(word, result)
                bot.send_message(message.from_user.id, "This is your link: " + link)
                bot.send_message(message.from_user.id, "The address is: " + street)
                bot.send_message(message.from_user.id, emojize("The price is: " + str(number) + " :heavy_dollar_sign:", use_aliases=True))
                bot.send_message(message.from_user.id, "Do you want to get the weather, here?")
                bot.register_next_step_handler(message, weather, city)
        else:
            bot.send_message(message.from_user.id, "The price is not compatible, write another one")
            bot.register_next_step_handler(message, price, result, city)
    except:
        bot.send_message(message.from_user.id, "Wrong price, write a real number")
        bot.register_next_step_handler(message, price, result, city)


def weather(message, city):
    word = message.text
    words = ["yes", "yeah", "ya", "sure", "of course", "yep", "da"]
    if word.lower() in words:
        current_weather, forecast_weather = weather_process(city)
        output_process(message, current_weather, forecast_weather)
    else:
        bot.send_message(message.from_user.id, "Ok, thank's for using our service")
bot.polling()
