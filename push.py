import requests,json,re
from loguru import logger
#from i18n import *
#from globals import load_config

class PUSH():
    def __init__(self,config,message):
        self.config = config
        self.headers = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
         }
        self.message = message
        if self.config['webhook']!='':
           
            if re.search('dingtalk',config['webhook']):
                self.ding_push()
            
            elif re.search('weixin',config['webhook']):
                self.wx_push()
            else:
                logger.error("unsupport_webhook")
                #logger.error(i18n_format("unsupport_webhook"))
        elif self.config['pushplus']!='':
            self.pushplus()
          
    
    def ding_push(self):
        # 构建请求数据
        msg = {
        "msgtype": "text",
        "text": {
            "content": self.message
        },
        "at": {
            "isAtAll": False
        }
        }
        # 对请求的数据进行json封装
        message_json = json.dumps(msg)
        # 发送请求
        info = requests.post(url=self.config['webhook'], data=message_json, headers=self.headers)
        # 打印返回的结果
        logger.info(info.text)
        
    def pushplus(self):
       
      
      token = self['push_plus'] #在pushpush网站中可以找到
      
      url = 'http://www.pushplus.plus/send'
      data = {
        "token":token,
        "title":self.message,
        "content":self.message
      }
      data=json.dumps(data).encode(encoding='utf-8')
      info=requests.post(url, json=data,headers=self.headers).json()
      logger.info(info.text)

    def wx_push():
        pass

if __name__ == "__main__":
    config={}
    config['webhook']=''
    config['pushplus']=''
    
    PUSH(config,"test")