# coding: utf-8

import requests
import pandas as pd

from bs4 import BeautifulSoup
from datetime import datetime as dt
from .db import table_scheme as ts


def html_text(url, encoding="UTF-8", trial=10):
    for t in range(trial):
        try:
            r = requests.get(url)
            r.encoding = encoding
            return True, r.text
        except ConnectionError:
            pass
    return False, url


def crawler(logger, engine, max_page=5, categories=[1, 2, 3, 4, 5, 6, 7, 8],
            update_time=None):
    """
    Crawling gunosy web page and get following data
        - article title
        - article body
        - published date of the article

     Parameter
    ----------------
    logger: logger instance to output log
    max_page: scraping page number
    update_time: scrape by the update_time
        ex) update_time is "2016-01-01", this code will scrape articles
            which published after "2016-01-01"

     Return
    ----------------
    df: dataframe which contains, [title, category_id, body, published_date]
    time: updated time for each columns
    """

    if update_time is None:
        update_time = ["2016-01-01T00:00:00"]*len(categories)

    assert len(categories) == len(update_time)
    logger.info("category:"+str(categories))
    logger.info("update time:"+str(update_time))
    logger.info("max page:"+str(max_page))

    # main loop
    # dat = []
    time = []
    for c, u_time in zip(categories, update_time):
        try:
            p = 0
            while p < max_page:
                p += 1
                logger.info("Category:%s,Page:%s" % (c, p))
                url = "https://gunosy.com/categories/%s?page=%s" % (c, p)
                html = html_text(url)
                if not html[0]:
                    logger.info("[NOT FOUND]")
                    # logger.info("[NOT FOUND] %s" % html[1])
                    continue
                # MAIN PROCESS (accumlate vectorize text data)
                try:
                    parser = "html.parser"
                    bsObj = BeautifulSoup(html[1], parser)
                except Exception:
                    parser = "html5lib"
                    bsObj = BeautifulSoup(html[1], parser)

                bsObj = bsObj.findAll("div", {"class": "list_content"})
                if len(bsObj) is 0:
                    logger.info("Category:%s, Page:%s  [NOT FOUND]" % (c, p))
                    continue
                for child in bsObj:  # article-wise iteration
                    child = child.find("div", {"class": "list_title"})
                    # if html error occured, then go next
                    html = html_text(child.a.get("href"))
                    if not html[0]:
                        logger.info("[NOT FOUND]")
                        # logger.info("[NOT FOUND] %s" % html[1])
                        continue
                    # scrape article
                    bsObj = BeautifulSoup(html[1], parser)
                    bs_ = bsObj.find("div", {"class": "article_header_text"})
                    title = bs_.h1.get_text().replace("'", " ").replace('"', " ")
                    bs_ = bsObj.find("li", {"class": "article_header_lead_date"})
                    published_date = bs_.get("content").split('+')[0]

                    text = ""
                    bs_ = bsObj.find("div", {"class": "article gtm-click"})
                    for child in bs_.findAll("p"):
                        text_ = child.get_text().replace("'", " ")
                        text += text_.replace('"', " ")
                    if u_time >= published_date:
                        break
                    else:
                        _index = ["date", "category_ind", "title", "contents"]
                        _data = [published_date, c, title, text]
                        df = pd.DataFrame(_data, index=_index).T
                        try:
                            df.to_sql(ts.article_contents.__tablename__, engine,
                                      if_exists='append', index=False)
                        except Exception as err:
                            logger.error(err)
        except Exception as err:
            logger.error(err)
        finally:
            time.append([c, dt.today().isoformat()])
    # df = pd.DataFrame(dat, columns=["date", "category_ind", "title",
    #                                 "contents"])
    time = pd.DataFrame(time, columns=["category_ind", "update_time"])
    logger.info("inserting time shaped "+str(time.shape))
    time.to_sql(ts.article_categories.__tablename__, engine,
                if_exists='append', index=False)
