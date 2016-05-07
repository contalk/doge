#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# ver: 1.0
# developer：doge
# wechat：towwen

#import httplib
#import urllib
import json
import socket
import sys
import string

import time
import thread
import threading

import math
import codecs
import traceback
import config

class Futu():

	PROTO_PRICE = 1001
	PROTO_GEAR = 1002
	PROTO_UNLOCK = 6006

	PROTO_HK_SET_ORDER = 6003
	PROTO_HK_SET_ORDER_STATUS = 6004
	PROTO_HK_UPDATE_ORDER = 6005
	PROTO_HK_ACCOUNT = 6007
	PROTO_HK_ORDER_LIST = 6008
	PROTO_HK_HOLD_LIST = 6009

	PROTO_US_SET_ORDER = 7003
	PROTO_US_SET_ORDER_STATUS = 7004
	PROTO_US_UPDATE_ORDER = 7005
	PROTO_US_ACCOUNT = 7007
	PROTO_US_ORDER_LIST = 7008
	PROTO_US_HOLD_LIST = 7009
	VERSION = '1'

	def __init__(self):
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.connect((config.g_host, config.g_port))
		self.lock = thread.allocate_lock()

	def __del__(self):
		self.s.close()

	def __check_stock_code(self, stock):
		stock = stock.strip().upper()
		arr = stock.split('.')
		if len(arr)==2:
			rs = {}
			rs['Market'] = arr[1]
			rs['StockCode'] = arr[0]
			return rs
		else:
			print('stock code error')
			return None

	def __get_market_code(self, market):
		market = market.upper()
		marketCode = {
			'HK':'1', 
			'US':'2', 
			'SH':'3', 
			'SZ':'4'
			}
		if marketCode.has_key(market):
			return marketCode[market]
		else:
			print('market code error')
			return None

	def __call(self, command, param):
		self.lock.acquire()
		try:
			req = {
				'Protocol':str(command),
				'ReqParam': param,
				'Version':self.VERSION
				} 		
			mystr = json.dumps(req) + '\n'
			self.s.send(mystr) 
			rsp = ""
			buf = self.s.recv(4096)
			mybuf = buf.split("\r\n")
			for rsp in mybuf:
				if len(rsp) > 2:
					try:
						rsp = rsp.decode('utf-8')
					except Exception, e:
						rsp = rsp.decode('gbk')
					r = json.loads(rsp)

					if r["Protocol"] == self.PROTO_US_SET_ORDER or r["Protocol"] == self.PROTO_HK_SET_ORDER or r["Protocol"] == self.PROTO_HK_SET_ORDER_STATUS or r["Protocol"] == self.PROTO_HK_UPDATE_ORDER:
						if r['ErrCode'] > 0 :
							print r['ErrCode'],r['ErrDesc']
					elif r['ErrCode'] == '0' :
						self.lock.release()
						return r["RetData"]
					else:
						print r['ErrCode'],r['ErrDesc']   			 			
		except Exception, e:
			exstr = traceback.format_exc()
			print exstr
		self.lock.release()   	
		return None

	def get_account(self, market):
		req = {
			'Cookie':config.g_uid,
		  	'EnvType':config.g_env,
		  	}
		if market.upper()=='HK':
			return self.__call(self.PROTO_HK_ACCOUNT, req)
		elif market.upper()=='US':
		  	return self.__call(self.PROTO_US_ACCOUNT, req)
		else:
		  	return None

	def unlock(self):
		req = {
			'Cookie':str(config.g_uid),
		  	'Password':str(config.g_pwd),
		  	}
		return self.__call(self.PROTO_UNLOCK, req)
	  
	def get_price(self, stock):
		r = self.__check_stock_code(stock)
		if r is not None:
			req = {
				'Market':self.__get_market_code(r['Market']),
			  	'StockCode':r['StockCode'],
				}
			data = self.__call(self.PROTO_PRICE, req)
			if(data is not None):
				for i in ('Cur','High','Low', 'Close', 'Open', 'LastClose', 'Turnover'):
				  	data[i] = round(float(data[i]) / 1000, 3)
				  	data['Vol'] = int(data['Vol'])
				return data
		return None

	def get_gear(self, stock, num = 10):
		r = self.__check_stock_code(stock)
		if r is not None:
			req = {
				'Market':self.__get_market_code(r['Market']),
			  	'StockCode':r['StockCode'],
			  	'GetGearNum':str(num)
				}
			data = self.__call(self.PROTO_GEAR, req)
			if data is not None:
				for i in data['GearArr']:
			  		i['BuyPrice'] = round(float(i['BuyPrice']) / 1000,3)
			  		i['BuyVol'] = int(i['BuyVol'])
			  		i['SellPrice'] = round(float(i['SellPrice']) / 1000,3)
			  		i['SellVol'] = int(i['SellVol'])
				return data['GearArr']
		return None

	#暂只支持限价 OrderType = 0 
	def buy(self, stock, price, amount):
		r = self.__check_stock_code(stock)
		if r is not None:
			#HK
			OrderType = 0
			Protocol = self.PROTO_HK_SET_ORDER
			if r['Market'] == 'US' :
				OrderType = 2
				Protocol = self.PROTO_US_SET_ORDER

			req = {
				'Cookie': str(config.g_uid),
				'OrderSide':'0',
				'OrderType':str(OrderType),
				'Price':str(int(math.floor(price * 1000))),
				'Qty': str(int(amount)),
				'StockCode':str(r['StockCode']),
				'EnvType': str(config.g_env)
				}
			return self.__call(Protocol, req)
		return None

	def sell(self, stock, price, amount):
		r = self.__check_stock_code(stock)
		if r is not None:
			#HK
			OrderType = 0
			Protocol = self.PROTO_HK_SET_ORDER
			if r['Market'] == 'US' :
				OrderType = 2
				Protocol = self.PROTO_US_SET_ORDER

			req = {
				'Cookie':str(config.g_uid),
				'OrderSide':'1',
				'OrderType':str(OrderType),
				'Price':str(int(math.floor(price * 1000))),
				'Qty': str(amount),
				'StockCode':str(r['StockCode']),
				'EnvType': str(config.g_env)
				}
			return self.__call(Protocol, req)
		return None

	def cancel(self, market, LocalID):
		Protocol = self.PROTO_HK_SET_ORDER_STATUS
		if market.upper() == 'US':
			Protocol = self.PROTO_US_SET_ORDER_STATUS

		req = {
			'Cookie':str(config.g_uid),
		  	'LocalID':str(LocalID),
		  	'SetOrderStatus':'0',
		  	'EnvType':str(config.g_env)
		  	}
		return self.__call(Protocol, req)

	def update(self, market, LocalID, price, amount):
		Protocol = self.PROTO_HK_UPDATE_ORDER
		if market.upper() == 'US':
			Protocol = self.PROTO_US_UPDATE_ORDER

		req = {
			'Cookie':str(config.g_uid),
		  	'LocalID':str(LocalID),
		  	'Price':int(math.floor(price * 1000)),
		  	'Qty': str(amount),
		  	'EnvType':str(config.g_env)
		  	}
		print req
		return self.__call(Protocol, req)

	def get_order_list(self, market):
		req = {
			'Cookie':str(config.g_uid),
		  	'EnvType':str(config.g_env)
		  	}
		if market.upper() == 'HK':
		  	return self.__call(self.PROTO_HK_ORDER_LIST, req)
		elif market.upper() == 'US':
		  	return self.__call(self.PROTO_US_ORDER_LIST, req)

	def get_order_stock(self, stock):
		r = self.__check_stock_code(stock)
		if r is not None:
			rows = {}
			rs = self.get_order_list(r['Market'])
			if rs is not None and rs.has_key('HKPositionArr'):
				rows = rs['HKPositionArr']
			if rs is not None and rs.has_key('USPositionArr'):
				rows = rs['USPositionArr']
			if len(rows) >  0:
				for row in rows:
					if row['StockCode'] == r['StockCode']:
						data = {}
						data['StockCode'] = row['StockCode']
						data['Qty'] = int(row['Qty'])
						data['CostPrice'] = round(float(row['CostPrice']) / 1000, 3)
						data['MarketVal'] = round(float(row['MarketVal']) / 1000, 3)
						return data
		return None

	def get_hold_list(self, market):
		req = {
			'Cookie':str(config.g_uid),
		  	'EnvType':str(config.g_env),
		  	}
		if market.upper() == 'HK':
			return self.__call(self.PROTO_HK_HOLD_LIST, req)
		elif market.upper() == 'US':
		  	return self.__call(self.PROTO_US_HOLD_LIST, req)

	def get_hold_stock(self, stock):
		r = self.__check_stock_code(stock)
		if r is not None:
			rows = {}
			rs = self.get_hold_list(r['Market'])
			if rs is not None and rs.has_key('HKPositionArr'):
				rows = rs['HKPositionArr']
			if rs is not None and rs.has_key('USPositionArr'):
				rows = rs['USPositionArr']
			if len(rows) >  0:
				for row in rows:
					if row['StockCode'] == r['StockCode']:
						data = {}
						data['StockCode'] = row['StockCode']
						data['Qty'] = int(row['Qty'])
						data['CostPrice'] = round(float(row['CostPrice']) / 1000, 3)
						data['MarketVal'] = round(float(row['MarketVal']) / 1000, 3)
						return data
		return None

	def get_tick_size(self, price):
		if  price <= 0.25:
			return 0.001 # 价格[0.05, 0.25] 每单位幅度变化 0.4% - 2%
		if price > 0.25 and price <= 0.5:
			return 0.005 # 2% - 1% 
		if price > 0.5 and price <= 10:
			return 0.01	# 2% - 0.1%
		if price > 10 and price <= 20:
			return 0.02 # 2% - 0.1%
		if price > 20 and price <= 100:
			return 0.05 # 0.25% - 0.05%
		if price > 100 and price <= 200:
			return 0.1 # 0.1% - 0.05%
		if price > 200 and price <= 500:
			return 0.2 # 0.1% - 0.04%
		if price > 500 and price <= 1000:
			return 0.5 # 0.1% - 0.05%
		if price >= 1000 and price <= 2000:
			return 1
		if price > 2000:
			return 2		
