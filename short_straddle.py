from NorenRestApiPy.NorenApi import NorenApi
import logging
from datetime import datetime
import threading
import math
import pandas as pd
import yaml
from tkinter import *
from tkinter import messagebox

class ShoonyaApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://shoonyatrade.finvasia.com/NorenWClientTP/', websocket='wss://shoonyatrade.finvasia.com/NorenWSTP/', eodhost='https://shoonya.finvasia.com/chartApi/getdata/')

#for debugging you can enable below line
#logging.basicConfig(level=logging.DEBUG)

#start of our program
api = ShoonyaApiPy()
with open('cred.yml') as f:
    cred = yaml.load(f, Loader=yaml.FullLoader)
ret = api.login(userid = cred['user'], password = cred['pwd'], twoFA=cred['factor2'], vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])

#getting atm strikes and names
def getsymbol_atm():
    nifty_bank = api.get_quotes('NSE','Nifty Bank')
    ltp = float(nifty_bank['lp'])
    mod = int(ltp)%50
    if mod < 50:
        atm= int(math.floor(ltp/100))*100
    else:
        atm= int(math.ceil(ltp/100))*100
    txt='BANKNIFTY JUN '+str(atm)
    strikes = api.searchscrip(exchange='NFO', searchtext=txt)
    strike = pd.DataFrame(strikes['values'])
    try:
        strike = strike.sort_values(by='weekly').iloc[0:2]
    except KeyError:
        strike
    return strike, atm

#executing order for banknifty straddle sell 
def atm_straddle_bnf():
    global ce_order, pe_order, ce, pe, qty
    
    if int(lot_entry.get()) > 0:
        pass
    else:
        messagebox.showerror("error", "Please Enter Lot size")
    
    ce_pe = getsymbol_atm()
    pe = ce_pe[0]['tsym'].iloc[0]
    ce = ce_pe[0]['tsym'].iloc[1]
    qty=int(lot_entry.get())*25
    ce_order, pe_order = api.place_order(buy_or_sell='S', product_type='I',
                        exchange='NFO', tradingsymbol=ce, 
                        quantity=qty, discloseqty=0,price_type='MKT',trigger_price=0,
                        retention='DAY', remarks='my_order_001'), api.place_order(buy_or_sell='S', product_type='I',
                        exchange='NFO', tradingsymbol=pe, 
                        quantity=qty, discloseqty=0,price_type='MKT',trigger_price=0,
                        retention='DAY', remarks='my_order_001')

#this feature you can add in UI if you want to minimize the margin or risk depending on range you choose.
def buy_hedge_bnf():
    hedge = getsymbol_atm()
    atm = hedge[1]+1000
    pe = ce_pe['tsym'].iloc[0]
    ce = ce_pe['tsym'].iloc[1]
    ce_order = api.place_order(buy_or_sell='B', product_type='I',
                        exchange='NFO', tradingsymbol=ce, 
                        quantity=25, discloseqty=0,price_type='MKT',trigger_price=0,
                        retention='DAY', remarks='my_order_001')
    pe_order = api.place_order(buy_or_sell='B', product_type='I',
                        exchange='NFO', tradingsymbol=pe, 
                        quantity=25, discloseqty=0,price_type='MKT',trigger_price=0,
                        retention='DAY', remarks='my_order_001')
    return ce_order, pe_order

#stop loss on current position(percentage based)
def atm_straddle_sl():
    global ce_sl, pe_sl
    sl_en = int(sl_entry.get())
    ce_lp = int(float(api.get_quotes('NFO',ce)['lp']))
    pe_lp = int(float(api.get_quotes('NFO',pe)['lp']))
    cesl, pesl = int(ce_lp*(sl_en*0.01+1)), int(pe_lp*(sl_en*0.01+1)) 
    
    orderno = ce_order['norenordno'] #from placeorder return value
    ce_sl = api.place_order(buy_or_sell='B', product_type='I',
                        exchange='NFO', tradingsymbol=ce, 
                        quantity=qty, discloseqty=0,price_type='SL-LMT',price = cesl+1,trigger_price=cesl-1,
                        retention='DAY', remarks='m')
    pe_sl = api.place_order(buy_or_sell='B', product_type='I',
                        exchange='NFO', tradingsymbol=pe, 
                        quantity=qty, discloseqty=0,price_type='SL-LMT',price=pesl+1,trigger_price=pesl-1,
                        retention='DAY', remarks='m')
    sl['celp']=ce_lp
    sl['ceorder']=ce_sl['norenordno']
    sl['pelp']=pe_lp
    sl['peorder']=pe_sl['norenordno']

#stop loss modify
def modify_straddle_sl():
    l = sl_modify.get()
    if l == 'c':
        ce_sl_modify = api.modify_order(exchange='NFO', tradingsymbol=ce, orderno=sl['ceorder'],
                        newquantity=qty, newprice_type='SL-LMT', newprice=sl['celp']+1, newtrigger_price=sl['celp']+1)
    elif l=='p':
        pe_sl_modify = api.modify_order(exchange='NFO', tradingsymbol=pe, orderno=sl['peorder'],
                        newquantity=qty, newprice_type='SL-LMT', newprice=sl['pelp']+1, newtrigger_price=sl['pelp']+1)  

#Scheduling of your straddle order
def time_straddle():
    h=int(hour.get())
    m=int(minute.get())
    s=int(second.get())
    now = datetime.now()        
    ct = now.replace(hour=h,minute=m,second=s)
    i = max(0,(ct-now).total_seconds())
    t = threading.Timer(i,atm_straddle_bnf)
    t.start()          

window=Tk()

window.title("Axel")
window.geometry('550x400')
window.config(bg='#C89D7C')


global sl
sl={}

l=Label(window, text="Short Straddle", bg='#C89D7C', font= ('Arial', 11, 'bold'))
l.grid(row=1,column=1,sticky = E, pady = 5)

l1=Label(window, text="Lot Size", bg='#C89D7C', font= ('Arial', 9, 'bold'))
l1.grid(row=2,column=0, sticky = W, padx = 10)

l2=Label(window, text="SL", bg='#C89D7C', font= ('Arial', 9, 'bold'))
l2.grid(row=2,column=1, sticky = W)

l3=Label(window, text="SL Modify", bg='#C89D7C', font= ('Arial', 9, 'bold'))
l3.grid(row=4,column=0, sticky = E,padx = 8, pady = 2)

l4=Label(window, text="Time", bg='#C89D7C', font= ('Arial', 9, 'bold'))
l4.grid(row=5,column=0, sticky = W, padx = 10)

l5=Label(window, text="Hour", bg='#C89D7C', font= ('Arial', 9, 'bold'))
l5.grid(row=6,column=0, sticky = W, padx = 10)

l6=Label(window, text="Minute", bg='#C89D7C', font= ('Arial', 9, 'bold'))
l6.grid(row=6,column=1, sticky = W)

l7=Label(window, text="Second", bg='#C89D7C', font= ('Arial', 9, 'bold'))
l7.grid(row=6,column=2, sticky = W)

lot_entry=StringVar()
e1=Entry(window,textvariable=lot_entry)
e1.grid(row=3,column=0, padx = 10)

sl_entry=StringVar()
e2=Entry(window,textvariable=sl_entry)
e2.grid(row=3,column=1, padx = 5)

sl_modify=StringVar()
e3=Entry(window,textvariable=sl_modify)
e3.grid(row=4,column=1, padx = 5)

hour=StringVar()
e4=Entry(window,textvariable=hour)
e4.grid(row=7,column=0, padx = 10)

minute=StringVar()
e5=Entry(window,textvariable=minute)
e5.grid(row=7,column=1)

second=StringVar()
e6=Entry(window,textvariable=second)
e6.grid(row=7,column=2, padx = 5)

b1=Button(window,text="Sell", width=10, command=atm_straddle_bnf, bg='#ff2c2c', relief="ridge")
b1.grid(row=3,column=2, sticky = W, padx=10)

b2=Button(window,text="SL", width=10, command=atm_straddle_sl, bg='#ff2c2c', relief="ridge")
b2.grid(row=3,column=3, sticky = W, padx=10)

b3=Button(window,text="Move to Cost", width=10, command=modify_straddle_sl, bg='#ff2c2c', relief="ridge")
b3.grid(row=4,column=2, sticky = W, padx=10, pady = 20)

b4=Button(window,text="Shoot", width=10, command=time_straddle, bg='#ff2c2c', relief="ridge")
b4.grid(row=7,column=3, sticky = W, padx=10)

window.mainloop()