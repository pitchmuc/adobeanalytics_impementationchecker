# -*- coding: utf-8 -*-
"""
@author: julien piccini
"""

import pandas as _pd
from selenium import webdriver as _webdriver
import time as _time
from urllib.parse import urlparse as _urlparse
#import numpy as _np
from pathlib import Path as _Path
_c_path = _Path.cwd() #get the current folder
_new_path = _c_path.joinpath('perf_checker') #create new folder
_new_path.mkdir(exist_ok=True) #create a new folder to store the data

#### 3/4G Testing
#driver.set_network_conditions(
#    offline=False,
#    latency=5,  # additional latency (ms)
#    download_throughput=500 * 1024,  # maximal throughput
#    upload_throughput=500 * 1024)  # maximal throughput

__js_assets_aa_function = """
list_perf = window.performance.getEntries()
list_asset = []
for(i=0;i<list_perf.length;i++){
	if(list_perf[i].name.indexOf('assets.adobedtm')!= -1 || list_perf[i].name.indexOf('b/ss')!= -1){
		list_asset.push(list_perf[i]);
	}
}
return list_asset
"""

__js_DOMperf_function = """
domperf = window.performance.getEntries()[0]
return domperf
"""

__js_href_function = """
list_a = Array.from(document.getElementsByTagName("a"));
list_href = [];
for (i=0;i<list_a.length;i++){list_href.push(list_a[i].href)}
return list_href
"""

def __newfilename(domain):
    """
    basic filename function
    """
    fmonth = _time.strftime("%m")
    fday = _time.strftime("%d")
    fhour = _time.strftime("%H")
    fminute = _time.strftime("%M")
    filename=_new_path.as_posix()+'/'+'crawl_'+domain+'_'+fmonth+'_'+fday+'_'+fhour+'_'+fminute
    return filename


def _returnDomain(url):
    l_domain = _urlparse(url).netloc.split('.')
    domain = '.'.join(l_domain[1:])
    return domain


def _setupBrowser(mobile,noCache=False):
    options = _webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('headless')
    if noCache:
        options.add_argument('--disable-application-cache')
    if mobile:
        mobile_emulation = { "deviceName": "Nexus 5" }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
    driver = _webdriver.Chrome(chrome_options=options)
    driver.implicitly_wait(3)
    return driver



def _get_requestInfo(url,driver,noCache=False,mobile=False,verbose=False):
    """ Function to retrieve info through requests"""
    requests=[]
    DOMperf=[]
    domain = _returnDomain(url)
    if noCache:
        driver = _setupBrowser(mobile,noCache=noCache)
    driver.get(url)
    _time.sleep(1)
    request = driver.execute_script(__js_assets_aa_function)
    requests.append(request)
    DOMperf.append(driver.execute_script(__js_DOMperf_function))
    list_href = driver.execute_script(__js_href_function)
    unique_href = list(set(list_href))
    clean_unique_href = [x for x in unique_href if (domain in x and '#' not in x)]
    to_do = clean_unique_href
    if verbose:
        pass
    if noCache:
        driver.close()
    return requests, to_do,DOMperf

def perfchecker(url,counter=10,noCache=False,mobile=False,verbose=False,export=True):
    """ This method will return a dataframe with the urls, the dimension retrieved and the value for each dimension to each URL.
    
    Parameters : 
        url : REQUIRED : can be an url or a list of url - if it is list the counter will be set automatically to the number of url you have passed
        counter : OPTIONAL : number of url to retrieved (default to 10)
        mobile : OPTIONAL : if you want to test for mobile website (default to False)
        verbose : OPTIONAL : if you want comments (default to False)
    """
    if type(url) == list:
        list_url = url
        counter = len(list_url)
    elif type(url) == str:
        list_url = [url]        
    #domain = _returnDomain(list_url[0])
    if noCache==False:
        driver = _setupBrowser(mobile,noCache=False)
    else:
        driver=None
    url_done = [] ##Check all the url crawled
    data_set = dict() ##Retrive data from asset performance check
    domPerf_set = dict()##retrieve data from dom performance check
    for u in range(counter):
        url_done.append(list_url[u])
        if u%20==0 and verbose:
            print(str(u)+' URL done')
        try:
            if noCache:
                requests, to_do, DOMperf = _get_requestInfo(list_url[u],driver,noCache=noCache,verbose=verbose)
            else:
                requests, to_do, DOMperf = _get_requestInfo(list_url[u],driver,verbose=verbose)
            for url_to_do in to_do:
                if url_to_do not in url_done:
                    list_url.append(url_to_do)
            data_set[list_url[u]] = requests[0]
            domPerf_set[list_url[u]] = DOMperf
        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)
    if noCache==False:
        driver.close()
    full_df = _pd.DataFrame()
    i=0
    for key in data_set.keys():##Asset dataframe building
        temp_1df = _pd.DataFrame()
        i+=1
        for dic in data_set[key]:
            temp_df = _pd.DataFrame.from_dict(dic,orient='index').T
            temp_df['url'] = key
            temp_df['url_nb'] = i
            temp_1df = temp_1df.append(temp_df,ignore_index=True)
        full_df = full_df.append(temp_1df,ignore_index=True)
    for col in list(full_df.columns):
        try:
            full_df[col] = full_df[col].astype(float)
        except:
            pass
#    full_df['script'] = full_df['name'].str.extract('7a/(.+?)\.')
    dom_df = _pd.DataFrame()###DOM dataframe building
    for key in domPerf_set.keys():
        temp_2df = _pd.DataFrame()
        for dic in domPerf_set[key]:
            temp_dom_df = _pd.DataFrame.from_dict(dic,orient='index').T
            temp_dom_df['url'] = key
            temp_2df = temp_2df.append(temp_dom_df,ignore_index=True)
        dom_df = dom_df.append(temp_2df)
    for col in list(dom_df.columns):
        try:
            dom_df[col] = dom_df[col].astype(float)
        except:
            pass
    if export:
        pass
        if verbose:
            print('your report is available on this folder '+_new_path.as_posix())
    return full_df,dom_df