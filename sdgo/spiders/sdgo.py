import scrapy
import json
from scrapy.http import FormRequest
from bs4 import BeautifulSoup

cookie = ''
srch_date = ''
num_pgs = 0

class SDGOSpider(scrapy.Spider):
    name = 'sdgo'
    start_urls = ['https://arcc-acclaim.sdcounty.ca.gov/search/Disclaimer?st=/search/SearchTypeRecordDate']

    def parse(self, response):
        global cookie
        cookie = str(response.request.headers.getlist('Cookie')[0]).replace('b\'ASP.NET_SessionId=','')[:-1]
        headers = {
        'Cookie' : 'cartButton=shown; ASP.NET_SessionId='+cookie+';'
        +' Group4=SearchGridForRecordDate={"SearchTypeRecordDate":{"NumberOfPages":{"show":"1","width":"75px"},'
        +'"DirectName":{"show":"1","width":"125px"},"IndirectName":{"show":"1","width":"*"},"InstrumentNumber":'
        +'{"show":"1","width":"100px"},"RecordDate":{"show":"1","width":"100px"},'
        +'"DocTypeDescription":{"show":"1","width":"75px"},"ParcelNumber":{"show":"1","width":"175px"},'
        +'"BookType":{"show":"1","width":"50px"},"SecondarySequenceNumber":{"show":"1","width":"75px"},'
        +'"BookPage":{"show":"1","width":"95px"}} };'
        +' AcclaimWebUserPreferencesCookie=UserDefaultAutoLoadImages%3Dtrue',
        }
        url = 'https://arcc-acclaim.sdcounty.ca.gov/search/Disclaimer?st=/search/SearchTypeRecordDate'
        return [FormRequest(url=url,headers=headers,formdata={'disclaimer':'true',},callback=self.parse_url1)]
    
    def parse_url1(self, response):
        global srch_date
        srch_date = self.srch_date
        url = 'https://arcc-acclaim.sdcounty.ca.gov/search/SearchTypeRecordDate?Length=6'
        return [FormRequest(url=url,formdata={'RecordDate':srch_date, 'X-Requested-With':'XMLHttpRequest'},callback=self.parse_url2)]
        
    def parse_url2(self, response):
        global cookie
        url = 'https://arcc-acclaim.sdcounty.ca.gov/Search/GridResults'
        headers = {
        'Cookie':'ASP.NET_SessionId='+cookie+'; Group4=SearchGridForRecordDate={"SearchTypeRecordDate":{"NumberOfPages":{"show":"1","width":"75px"},'
        +'"DirectName":{"show":"1","width":"125px"},"IndirectName":{"show":"1","width":"*"},"InstrumentNumber":{"show":"1","width":"100px"},'
        +'"RecordDate":{"show":"1","width":"100px"},"DocTypeDescription":{"show":"1","width":"75px"},"ParcelNumber":{"show":"1","width":"175px"},'
        +'"BookType":{"show":"1","width":"50px"},"SecondarySequenceNumber":{"show":"1","width":"75px"},"BookPage":{"show":"1","width":"95px"}} };'
        +' AcclaimWebUserPreferencesCookie=UserDefaultSearchGridRowPageSize=500&UserPurchaseHistoryDateType=PurchaseDate&UserDefaultPaymentOption=CreditCard'
        +'&UserDefaultEmailPaymentConfirmationOption=True&UserDefaultAutoLoadImages=True&UserDefaultAutoCompleteEnabled=False',
        'X-Requested-With':'XMLHttpRequest',
        }
        return [FormRequest(url=url,headers=headers,formdata={'page':'1','size':'500'},callback=self.parse_url3)]
    
    def parse_url3(self, response):
        global cookie
        global num_pgs
        json_data = json.loads(response.body)['data']
        if num_pgs == 0:
            num_pgs = int(int(json.loads(response.body)['total']) / 500)
            if int(int(json.loads(response.body)['total']) - (500 * num_pgs)) > 0:
                num_pgs += 1
        for pg_n in range(num_pgs):
            for i in range(len(json_data)):
                doc_num = str(json_data[i]['InstrumentNumber'])
                apn = str(json_data[i]['ParcelNumber'])
                url = 'https://arcc-acclaim.sdcounty.ca.gov/details/documentdetails/'+str(json_data[i]['TransactionItemId'])+'/['+str(i+1)+']/'+str(pg_n+1)+'/500'
                yield scrapy.Request(url=url, callback=self.parse_url4,meta={'doc_num': doc_num, 'apn':apn})
            if pg_n != num_pgs-1:
                url = 'https://arcc-acclaim.sdcounty.ca.gov/Search/GridResults'
                headers = {
                'Cookie':'ASP.NET_SessionId='+cookie+'; Group4=SearchGridForRecordDate={"SearchTypeRecordDate":{"NumberOfPages":{"show":"1","width":"75px"},'
                +'"DirectName":{"show":"1","width":"125px"},"IndirectName":{"show":"1","width":"*"},"InstrumentNumber":{"show":"1","width":"100px"},'
                +'"RecordDate":{"show":"1","width":"100px"},"DocTypeDescription":{"show":"1","width":"75px"},"ParcelNumber":{"show":"1","width":"175px"},'
                +'"BookType":{"show":"1","width":"50px"},"SecondarySequenceNumber":{"show":"1","width":"75px"},"BookPage":{"show":"1","width":"95px"}} };'
                +' AcclaimWebUserPreferencesCookie=UserDefaultSearchGridRowPageSize=500&UserPurchaseHistoryDateType=PurchaseDate&UserDefaultPaymentOption=CreditCard'
                +'&UserDefaultEmailPaymentConfirmationOption=True&UserDefaultAutoLoadImages=True&UserDefaultAutoCompleteEnabled=False',
                'X-Requested-With':'XMLHttpRequest',
                }                
                yield [FormRequest(url=url,headers=headers,formdata={'page':str(pg_n+2),'size':'500'},callback=self.parse_url3)]

    def parse_url4(self, response):
        doc_num = response.meta.get('doc_num')
        apn = response.meta.get('apn')
        opt_hdr = ['address','apn','block','city','county','description','doc_number','doc_type','gcp_link','lot','name','record_date','role','sec','state','transfer_amount','unit','zipcode']
        soup = BeautifulSoup(response.body,'lxml')
        doc_type = soup.findAll('div', {'class':"listDocDetails"})[1].text.strip()
        rec_date = soup.find('div', {'class':"formInput"}).text.strip()
        if len(list(filter(None, soup.findAll('div', {'class':"listDocDetails"})))) >= 3:
            li_gtr = soup.findAll('div', {'class':"listDocDetails"})[2].findAll('span')
            role = soup.findAll('div', {'class':"listDocDetails"})[2].find_previous('div').text
            for gtr in li_gtr:
                res = ['',apn.replace('None',''),'','','San Diego','',doc_num,doc_type,'','',gtr.text.strip(),rec_date,role.strip().replace(':',''),'','CA','','','']
                yield dict(zip(opt_hdr,res))
        if len(list(filter(None, soup.findAll('div', {'class':"listDocDetails"})))) >= 4:
            li_gte = soup.findAll('div', {'class':"listDocDetails"})[3].findAll('span')
            role = soup.findAll('div', {'class':"listDocDetails"})[3].find_previous('div').text
            for gte in li_gte:
                res = ['',apn.replace('None',''),'','','San Diego','',doc_num,doc_type,'','',gte.text.strip(),rec_date,role.strip().replace(':',''),'','CA','','','']
                yield dict(zip(opt_hdr,res))