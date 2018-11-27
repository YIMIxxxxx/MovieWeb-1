# -*- coding: utf-8 -*-
import scrapy
import re
from maoyan.items import MaoyanItem
import time, random
from maoyan.number_decode import getNumber


year_list = ['11','12','13','14']
year_flag = 0


class MaoyanSpiderSpider(scrapy.Spider):
    global year_flag
    global year_list
    name = 'maoyan_spider'
    allowed_domains = ['maoyan.com/films']
    start_urls = ['http://maoyan.com/films?showType=3&yearId=10']

    def parse(self, response):
        global year_flag
        movie_list = response.xpath("//div[@class='channel-detail movie-item-title']/a/@href").extract()
        for url_item in movie_list:
            next_link = url_item
            if next_link:
                yield scrapy.Request("http://maoyan.com"+next_link,callback = self.sub_page, dont_filter = True)
        next_page = response.xpath("//div[@class='movies-pager']/ul/li/a[contains(text(),'下一页')]/@href").extract_first()
        if next_page:
            yield scrapy.Request("https://maoyan.com/films" + next_page, callback = self.parse, dont_filter=True)
        elif year_flag < 3:
            yield scrapy.Request("https://maoyan.com/films?showType=3&yearId=" + year_list[year_flag],callback = self.parse, dont_filter = True)
            year_flag += 1
        pass

    def sub_page(self, response):
        time.sleep(random.random()*3)
        #print(re.search(r"url\('(?P<font>.+?woff)'", response.text).group('font'))
        movie_item = MaoyanItem()
        #电影名称
        movie_item['name'] = response.xpath("//h3[@class='name']/text()").extract_first()
        #上映日期
        movie_item['date'] = str(response.xpath("//ul/li[@class='ellipsis'][contains(text(),'上映')]/text()").extract_first()).replace('大陆上映','')
        #导演与演员
        director_path = "//div[@class='celebrity-group']/div[@class='celebrity-type'][contains(text(),'导演')][not(contains(text(),'副导演'))]/../ul/li/div[@class='info']/a[1]/text()"
        movie_item['director'] = str(response.xpath(director_path).extract_first()).replace(' ','').replace('\n','').replace('\\n','')
        actor_path = "//div[@class='celebrity-group']/div[@class='celebrity-type'][contains(text(),'演员')]/../ul/li/div[@class='info']/a[1]/text()"
        items = response.xpath(actor_path).extract()
        actors = []
        flag = 0
        for item in items:
            if flag > 10:
                break
            item = str(item).replace('\\n','').replace(' ','').replace('\n','')
            if item not in actors and item != ',':
                actors.append(item)
                flag = flag + 1
        seperation = ','
        movie_item['actors'] = seperation.join(actors)

        #电影类型
        movie_type = str(response.xpath("//div[@class='movie-brief-container']/ul/li[1]/text()").extract_first())
        if movie_type and '分钟' not in movie_type:
            movie_item['type'] = movie_type

        #字符解码文件url
        url = re.search(r"url\('(?P<font>.+?woff)'", response.text).group('font')
        #评分数据
        score = response.xpath("//div[@class='movie-index-content score normal-score']/span/span[@class='stonefont']/text()").extract_first()

        money = response.xpath("//div[@class='movie-index-content box']/span[@class='stonefont']/text()").extract_first()
        unit = response.xpath("//div[@class='movie-index-content box']/span[@class='unit']/text()").extract_first()

        decode = getNumber(url, [score, money])
        score_decode = decode[0]
        money_decode = decode[1]

        if score_decode:
            movie_item['score'] = score_decode
        else:
            movie_item = None

        if money_decode:
            if unit == '亿':
                money = money_decode * 100000000
            elif unit == '万':
                money = money_decode * 10000
            movie_item['box_office'] = money
        else:
            movie_item['box_office'] = None

        yield movie_item
        #people_part = response.xpath("//div[@class='mod-title']/a[@class='more']/@href")
        
        pass


