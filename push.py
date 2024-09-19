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
         self.webhook=config['webhook_token']
        except:
            logger.error("webhook_not_set")
            #logger.error(i18n_format("webhook_not_set"))
            self.webhook=''
        #push_plus
        try:
            self.pushplus=config['pushplus_token']
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
        #bark
        try:
            self.bark_token=config['bark_token']
        except:
            logger.error("bark_not_set")
            #logger.error(i18n_format("bark_not_set"))
            self.bark_token=""
        
                  
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
        if self.pushplus!='':
            self.pushplus()
        if self.bark!='':
            self.bark() 
        if self.smtp_mail_host and self.smtp_mail_pass and self.smtp_sender and self.smtp_receivers: 
            self.smtp()
        if self.wx_push!='': 
            self.wx_push()  

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
       
      
      token = self.pushplus_token #在pushpush网站中可以找到
      
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
        mail_host = self.smtp_mail_host 
        #163用户名
        mail_user = self.smtp_mail_user  
        #密码(部分邮箱为授权码) 
        mail_pass = self.smtp_mail_pass   
        #邮件发送方邮箱地址
        sender = self.smtp_sender  
        #邮件接受方邮箱地址，注意需要[]包裹，这意味`着你可以写多个邮件地址群发
        receivers = self.smtp_receivers  

        #设置email信息
        #邮件内容设置
        message = MIMEText(self.message,'plain','utf-8')
        #邮件主题       
        message['Subject'] = 'BHYG有新推送消息' 
        #发送方信息
        message['From'] = sender 
        #接受方信息     
        message['To'] = receivers  

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
        data={
            "title":"BHYG有新推送消息",
            "body":self.message,
            "level":"timeSensitive",
            #推送中断级别。 
#active：默认值，系统会立即亮屏显示通知
#timeSensitive：时效性通知，可在专注状态下显示通知。
#passive：仅将通知添加到通知列表，不会亮屏提醒。"""   
            "badge":1,
            "icon":"https://ys.mihoyo.com/main/favicon.ico",
            "group":"BHYG", 
            "isArchive":1
        }
        url=self.bark_token
        try:
          info=requests.post(url,json=data).json()
          logger.info("bark_send_success")
          #logger.info(i18n_format("bark_send_success"))
        except Exception as e:
          logger.error(e)

if __name__ == "__main__":
    config={}
    config['webhook_token']=''
    config['pushplus_token']=''
    config['bark_token']=""
    self=PUSH(config)
    PUSH.push(self,"test")