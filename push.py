import smtplib
import requests,json,re
from loguru import logger
#from i18n import *
#from globals import load_config

class PUSH():
    def __init__(self,config):
        self.config = config
        self.headers = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
         }
        #webhook
        try:
         self.webhook=config['webhook']
        except:
            logger.error("webhook_not_set")
            #logger.error(i18n_format("webhook_not_set"))
            self.webhook=''
        #push_plus
        try:
            self.pushplus=config['pushplus']
        except:
            logger.error("pushplus_not_set")
            #logger.error(i18n_format("pushplus_not_set"))
            self.pushplus=''
        #smtp
        try:
            self.smtp_mail_host=config['smtp_mail_host']
            self.smtp_mail_user=config['smtp_mail_user']
            self.smtp_mail_pass=config['smtp_mail_pass']
            self.smtp_sender=config['smtp_sender']
            self.smtp_receivers=config['receivers']
        except:
            logger.error("smtp_not_set")
            #logger.error(i18n_format("smtp_not_set"))
            self.smtp_mail_host=""
            self.smtp_mail_user=""
            self.smtp_mail_pass=""
            self.smtp_sender=""
            self.smtp_receivers=['']
        
                  
    def push(self,message):
        self.message = message
        if self.webhook!='':
           
            if re.search('dingtalk',config['webhook']):
                self.ding_push()
            
            elif re.search('weixin',config['webhook']):
                self.wx_push()
            else:
                logger.error("unsupport_webhook")
                #logger.error(i18n_format("unsupport_webhook"))
        if self.config['pushplus']!='':
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

    def wx_push(self):
        pass
    
    def smtp(self):
        from email.mime.text import MIMEText
        #设置服务器所需信息
        #163邮箱服务器地址
        mail_host = 'smtp.aliyun.com'  
        #163用户名
        mail_user = 'dorayaki@aliyun.com'  
        #密码(部分邮箱为授权码) 
        mail_pass = '20001116ye'   
        #邮件发送方邮箱地址
        sender = 'dorayaki@aliyun.com'  
        #邮件接受方邮箱地址，注意需要[]包裹，这意味`着你可以写多个邮件地址群发
        receivers = ['dorayaki@aliyun.com']  

        #设置email信息
        #邮件内容设置
        message = MIMEText(self.message,'plain','utf-8')
        #邮件主题       
        message['Subject'] = 'BHYG有新推送消息' 
        #发送方信息
        message['From'] = sender 
        #接受方信息     
        message['To'] = receivers[0]  

        #登录并发送邮件
        try:
            smtpObj = smtplib.SMTP() 
            #连接到服务器
            smtpObj.connect(mail_host,25)
            #登录到服务器
            smtpObj.login(mail_user,mail_pass) 
            #发送
            smtpObj.sendmail(
                sender,receivers,message.as_string()) 
            #退出
            smtpObj.quit() 
            #logger.info(i18n_format("send_success"))
            logger.info("send_success")
        except smtplib.SMTPException as e:
            print('error',e) #打印错误
            logger.error(e)
        
    def bark(self):
        pass

if __name__ == "__main__":
    config={}
    config['webhook']=''
    config['pushplus']=''
    
    self=PUSH(config)
    PUSH.push(self,"test")