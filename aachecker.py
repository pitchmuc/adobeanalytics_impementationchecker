# -*- coding: utf-8 -*-
"""
This library is using selenium to check the implementation of Adobe Analyitcs on your website. 
It works on Python 3. 

@author: julienpiccini
"""
import pandas as _pd
from selenium import webdriver as _webdriver
import time as _time
from urllib.parse import urlparse as _urlparse
import numpy as _np
from pathlib import Path as _Path
_c_path = _Path.cwd() #get the current folder
_new_path = _c_path.joinpath('implementation_checker') #create new folder
_new_path.mkdir(exist_ok=True) #create a new folder to store the data

__js_request_function = """
list_perf = window.performance.getEntries()
for(i=0;i<list_perf.length;i++){
	if(list_perf[i].name.indexOf('.sc.omtrdc.net')!= -1){
		request = list_perf[i].name;
	}
}
dec_request = decodeURIComponent(request)
return dec_request
"""

__js_href_function = """
list_a = Array.from(document.getElementsByTagName("a"));
list_href = [];
for (i=0;i<list_a.length;i++){list_href.push(list_a[i].href)}
return list_href
"""
__js_global_loop = "return s['{}']"

_dict_global = {
        "website":"",
        "crawl_date":"",
        "URL done" : "",
        "URL error": "",
        }

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

def __adobe_initiator():
    eVars = ['eVar'+str(x) for x in range(200)]
    param_evars = ['v'+str(x) for x in range(200)]
    dict_evar = dict(zip(eVars, param_evars))
    
    props = ["prop"+str(x) for x in range(1,75)]
    param_props = ["c"+str(x) for x in range(1,75)]
    dict_prop = dict(zip(props, param_props))
    dict_other = {'pageURL':'g',
    "server":"server ",
    "channel":"ch",
    "currencyCode" : "cc",
    "pageName":"pageName",
    "events":"events", 
    "list1":"l1",
    "list2":"l2",
    "list3":"l3",
    "marketingCloudVisitorID" : "mid",
    "account" : "account"
    }
    key_list = list(dict_other.keys()) + list(dict_prop.keys())+ list(dict_evar.keys())
    value_list = list(dict_other.values()) + list(dict_prop.values())+ list(dict_evar.values())
    translate_dict = dict(zip(key_list,value_list))
    
    dict_full={}
    for key in key_list:
        dict_full[key] = []
    
    return dict_full, key_list, value_list, translate_dict

def _returnDomain(url):
    l_domain = _urlparse(url).netloc.split('.')
    domain = '.'.join(l_domain[1:])
    return domain

def _setupBrowser(mobile):
    options = _webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('headless')
    if mobile:
        mobile_emulation = { "deviceName": "Nexus 5" }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
    driver = _webdriver.Chrome(chrome_options=options)
    driver.implicitly_wait(3)
    return driver

def _get_urlInfoFast(url_list=[],url_done=[],requests=[],mobile=False,verbose=False):
    """ Function to retrieve info through requests"""
    done = tuple(url_done)
    domain = _returnDomain(url_list[0])
    driver = _setupBrowser(mobile)
    driver.get(url_list[0])
    done_url = url_done +[url_list[0]]
    del url_list[0]
    _time.sleep(1)
    request = driver.execute_script(__js_request_function)
    requests.append(request)
    list_href = driver.execute_script(__js_href_function)
    unique_href = list(set(list_href))
    clean_unique_href = [x for x in unique_href if (domain in x and '#' not in x and x not in done)]
    to_do = url_list+clean_unique_href
    if verbose:
        print('url done : '+str(len(done_url)))
    return requests, to_do, done_url

def _analyze_requests(requests,verbose=False):
    """ From urlFast, parse and analyste the requests"""
    dict_full, key_list, value_list, translate_dict = __adobe_initiator()
    if verbose:
        print('Analyzing Requests: Initiated')
    url_post=[]
    for request in requests:
        try : 
            l_request = request.split('&')
            if len(l_request) ==1 : 
                url_post.append(request)
            l_param = [x.split('=',1)[0] for x in l_request if '=' in x]
            l_p_value = [x.split('=',1)[1] for x in l_request if '=' in x]
            dict_value = dict(zip(l_param, l_p_value))
            for key in dict_full.keys():
                val = translate_dict[key] 
                if val in dict_value.keys():
                    dict_full[key].append(dict_value[val])
                else:
                    dict_full[key].append(_np.nan)
        except:
            url_post.append(request)
    df = _pd.DataFrame(dict_full)
    df = df.dropna(axis=0,how='all')
    return df, url_post

def _get_urlInfoSlow(url_list=[],url_done=[],full_dict=None,list_keys=[],mobile=False,verbose=False):
    """ Function to retrieve info through javascript loop """
    done = tuple(url_done)
    dict_full=full_dict
    key_list = list_keys
    l_domain = _urlparse(url_list[0]).netloc.split('.')
    domain = '.'.join(l_domain[1:])
    driver = _setupBrowser(mobile)
    driver.get(url_list[0])
    done_url = url_done +[url_list[0]]
    del url_list[0]
    _time.sleep(1)
    for key in key_list:##Call key_list from mother method
        element = driver.execute_script(__js_global_loop.format(key))
        if element != "undefined":
            dict_full[key].append(element) ##Call dict_full from mother method
        else:
            dict_full[key].append(_np.nan)
    list_href = driver.execute_script(__js_href_function)
    unique_href = list(set(list_href))
    clean_unique_href = [x for x in unique_href if (domain in x and '#' not in x and x not in done)]
    to_do = url_list+clean_unique_href
    if verbose:
        print('url done : '+str(len(done_url)))
    return dict_full, to_do, done_url

def _dataGrab(list_url,counter=10,fast_method=True,mobile=False,verbose=False):
    """ Intermediate function """
    dict_full, key_list, value_list, translate_dict = __adobe_initiator()
    if verbose:
        print('Data Initialisation : done')
    done_url = []
    url_error = []
    requests = []
    count = 0
    if verbose:
        if fast_method:
            print('Fast Method : Initiated')
        else:
            print('Slow Method : Initiated')
    while count < counter:
        try :
            if fast_method:
                requests, list_url, done_url = _get_urlInfoFast(url_list=list_url,requests=requests,url_done=done_url,verbose=verbose)
                count +=1
                if verbose : 
                    print('url to do : '+ str(counter-count))
            else:
                dict_full, list_url, done_url = _get_urlInfoSlow(url_list=list_url,url_done=done_url,full_dict=dict_full,list_keys=key_list,verbose=verbose)
                count +=1
                if verbose : 
                    print('url to do : '+ str(counter-count))
        except :
            url_error.append(list_url[0])
            del list_url[0]
    if fast_method:
        return requests, list_url, done_url, url_error
    else:
        return dict_full, list_url, done_url, url_error

def checker(url,counter=10,mobile=False,fast_method=True,verbose=False,export=True):
    """ This method will return a dataframe with the urls, the dimension retrieved and the value for each dimension to each URL.
    
    Parameters : 
        url : REQUIRED : can be an url or a list of url - if it is list the counter will be set automatically to the number of url you have passed
        counter : OPTIONAL : number of url to retrieved (default to 10)
        mobile : OPTIONAL : if you want to test for mobile website (default to False)
        fast_method : OPTIONAL : if you try to catch the GET request or read all possible dimensions on the page. (default to True)
        verbose : OPTIONAL : if you want comments (default to False)
    
    """
    if type(url) == list:
        list_url = url
        counter = len(list_url)
    elif type(url) == str:
        list_url = [url]        
    domain = _returnDomain(list_url[0])
    data, list_url, url_done, url_error = _dataGrab(list_url,fast_method=fast_method,counter=counter,mobile=mobile,verbose=verbose)
    if fast_method:
        df, url_post = _analyze_requests(data,verbose=verbose)
        _dict_global['URL POST'] = url_post
    else :
        df = _pd.DataFrame(data)
    _dict_global['website'] = domain
    _dict_global['crawl_date'] = _time.strftime('%Y-%m-%d %H:%M')
    _dict_global['URL done'] = len(url_done)
    _dict_global['URL error'] = len(url_error)
    df_summary = _pd.DataFrame.from_dict(_dict_global,orient='index')
    df_summary.index.name = 'data'
    df_summary.columns = ['summary']
    df_summary.reset_index(inplace=True)#data frame for summary
    df1 = df.dropna(axis=1,how='all')#Clean data
    if export:
        filename = __newfilename(domain)
        writer = _pd.ExcelWriter(filename+'.xlsx', engine='xlsxwriter')##Create engine for xlsx file
        df_summary.to_excel(writer, sheet_name='Summary',index=False)
        df1.to_excel(writer, sheet_name='Data',index=False)
        writer.save()
        if verbose:
            print('your report is available on this folder '+_new_path.as_posix())
    return df1


def compareFile(df1,df2):
    """ Return the difference between the first dataframe and the second dataframe in a dataframe, also columns added and columns removed.
    The base is the first parameter
    Parameters : 
        df1 : REQUIRED : dataframe, can be the output of the crawler. Use a the base. 
        df2 : REQUIRED : dataframe, can be the output of the crawler
    """
    file_date = __newfilename()
    if df1.index.name is not 'pageURL':
        df1.set_index('pageURL',inplace=True)
    if df2.index.name is not 'pageURL':
        df2.set_index('pageURL',inplace=True)
    diff_cols = list(set(df1.columns) - set(df2.columns))
    df1_cols = list(df1.columns)
    new_cols = [x for x in diff_cols if x not in df1_cols]
    less_cols = [x for x in diff_cols if x in df1_cols]
    col_to_do = [x for x in df1_cols if x not in less_cols]
    new_dict = {}
    new_dict['pageURL'] = []
    for col in col_to_do:
        new_dict[col] = []
    for url in df1.index:
        if url in list(df2.index):
            new_dict['pageURL'].append(url)
            for col in col_to_do:
                if df1.at[url,col] == df2.at[url,col]:
                    new_dict[col].append(True)
                else:
                    new_dict[col].append(False)
    df_diff = _pd.DataFrame(new_dict)
    df_diff.to_csv(_new_path.as_posix()+'/'+'diff_'+file_date+'.csv',index=False, sep='\t')
    with open(_new_path.as_posix()+'/'+'new_dimensions.txt','w') as nd:
        for new in new_cols:
            nd.writelines(new)
    with open(_new_path.as_posix()+'/'+'remove_dimensions.txt','w') as rd:
        for new in less_cols:
            rd.writelines(new)
    return df_diff, new_cols, less_cols