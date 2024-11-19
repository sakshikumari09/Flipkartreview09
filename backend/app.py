import re
import os
import nltk
import joblib
import requests
import numpy as np
from bs4 import BeautifulSoup
import urllib.request as urllib
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from wordcloud import WordCloud, STOPWORDS
from flask import Flask, jsonify, request
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

def clean(x):
    x = re.sub(r'[^a-zA-Z ]', ' ', x)  # replace everything that's not an alphabet with a space
    x = re.sub(r'\s+', ' ', x)  # replace multiple spaces with one space
    x = re.sub(r'READ MORE', '', x)  # remove READ MORE
    x = x.lower()
    x = x.split()
    y = []
    for i in x:
        if len(i) >= 3:
            if i == 'osm':
                y.append('awesome')
            elif i == 'nyc':
                y.append('nice')
            elif i == 'thanku':
                y.append('thanks')
            elif i == 'superb':
                y.append('super')
            else:
                y.append(i)
    return ' '.join(y)

def extract_all_reviews(url, clean_reviews, org_reviews, customernames, commentheads, ratings):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'}
    req = urllib.Request(url, headers=headers)
    with urllib.urlopen(req) as u:
        page = u.read()
        page_html = BeautifulSoup(page, "html.parser")

    reviews = page_html.find_all('div', {'class': 't-ZTKy'})
    commentheads_ = page_html.find_all('p', {'class': '_2-N8zT'})
    customernames_ = page_html.find_all('p', {'class': '_2sc7ZR _2V5EHH'})
    ratings_ = page_html.find_all('div', {'class': ['_3LWZlK _1BLPMq', '_3LWZlK _32lA32 _1BLPMq', '_3LWZlK _1rdVr6 _1BLPMq']})

    for review in reviews:
        x = review.get_text()
        org_reviews.append(re.sub(r'READ MORE', '', x))
        clean_reviews.append(clean(x))

    for cn in customernames_:
        customernames.append('~' + cn.get_text())

    for ch in commentheads_:
        commentheads.append(ch.get_text())

    ra = []
    for r in ratings_:
        try:
            if int(r.get_text()) in [1, 2, 3, 4, 5]:
                ra.append(int(r.get_text()))
            else:
                ra.append(0)
        except:
            ra.append(r.get_text())

    ratings += ra
    time.sleep(1)

@app.route('/api/result', methods=['POST'])
def result():
    data = request.json
    url = data['reqdata']['url']
    nreviews = int(data['reqdata']['nreviews'])

    clean_reviews = []
    org_reviews = []
    customernames = []
    commentheads = []
    ratings = []

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'}
    req = urllib.Request(url, headers=headers)
    with urllib.urlopen(req) as u:
        page = u.read()
        page_html = BeautifulSoup(page, "html.parser")
    

    proname = page_html.find_all('span', {'class': 'B_NuCI'})[0].get_text()
    price = page_html.find_all('div', {'class': '_30jeq3 _16Jk6d'})[0].get_text()

    all_reviews_url = page_html.find_all('div', {'class': 'col JOpGWq'})[0]
    all_reviews_url = all_reviews_url.find_all('a')[-1]
    all_reviews_url = 'https://www.flipkart.com' + all_reviews_url.get('href')
    url2 = all_reviews_url + '&page=1'

    while True:
        x = len(clean_reviews)
        extract_all_reviews(url2, clean_reviews, org_reviews, customernames, commentheads, ratings)
        url2 = url2[:-1] + str(int(url2[-1]) + 1)
        if x == len(clean_reviews) or len(clean_reviews) >= nreviews:
            break

    org_reviews = org_reviews[:nreviews]
    clean_reviews = clean_reviews[:nreviews]
    customernames = customernames[:nreviews]
    commentheads = commentheads[:nreviews]
    ratings = ratings[:nreviews]

    for_wc = ' '.join(clean_reviews)
    wcstops = set(STOPWORDS)
    wc = WordCloud(width=1400, height=800, stopwords=wcstops, background_color='white').generate(for_wc)
    plt.figure(figsize=(20, 10), facecolor='k', edgecolor='k')
    plt.imshow(wc, interpolation='bicubic')
    plt.axis('off')
    plt.tight_layout()
    CleanCache(directory='static/images')
    plt.savefig('static/images/woc.png')
    plt.close()

    d = []
    for i in range(len(org_reviews)):
        x = {'review': org_reviews[i], 'cn': customernames[i], 'ch': commentheads[i], 'stars': ratings[i]}
        if x['stars'] != 0:
            x['sent'] = 'POSITIVE' if x['stars'] > 2 else 'NEGATIVE'
        d.append(x)

    np, nn = sum(1 for i in d if i['sent'] == 'POSITIVE'), sum(1 for i in d if i['sent'] == 'NEGATIVE')

    result = {
        "product_name": proname,
        "price": price,
        "reviews": d,
        "total_reviews": len(clean_reviews),
        "negative_reviews": nn,
        "positive_reviews": np
    }
    return jsonify(result)

@app.route('/')
def home():
    return "Hello, World!"

class CleanCache:
    def __init__(self, directory=None):
        self.clean_path = directory
        if os.listdir(self.clean_path) != list():
            for fileName in os.listdir(self.clean_path):
                os.remove(os.path.join(self.clean_path, fileName))

if __name__ == '__main__':
    app.run(debug=True, port=6767)
