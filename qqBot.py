import json
import requests
import time
from flask import  Flask,request
import re
class qqBotException(Exception):
    def __init__(self,e_str):
        self.e_str=e_str
    def __str__(self):
        return self.e_str


'''Config： 配置文件加载器'''
'''
Config文件字段定义:
    （1）funcDict:{"功能名":true or false}
    （2）group:{ str(group_id):{group_config} }        
                    group_config-------- saveFlag:boolean    savePath:string       welcomeFlag:boolean   welcomeStr:str and CQ        pauseFlag:boolean      superUser:list  
    （3）sendUrl
    （4）myQQ
    （5）
    （6）private_config
'''
class Config:
    def __init__(self,fileName="config"):
        with open(fileName, "r") as filePtr:
            self.Config = json.loads(filePtr.read())
    def get(self,keyName):
        try:
            return self.Config[keyName]
        except:
            return None
    def set(self,keyName,value):
        self.Config[keyName]=value
    def printConfig(self):
        print(self.Config)
    def writeBackPack(self):
        fileName="backPack--"+str(int(time.time()))
        print(type(fileName))
        with open(fileName,'w') as filePtr:
            filePtr.write(json.dumps(self.Config))
    def writeConfig(self,fileName="config"):
        with open(fileName,'w') as filePtr:
            filePtr.write(json.dumps(self.Config))
    def reload(self,fileName):
        with open(fileName, "r") as filePtr:
            self.Config = json.loads(filePtr.read())

'''群管理'''
class Group:
    def __init__(self,group_id,config,ipCreater=0):
        self.config=config
        self.ipCreater=ipCreater
        self.myQQ=self.config.get('myQQ')
        if(self.myQQ==None):
            raise qqBotException("配置文件-myQQ字段格式错误！")
        self.str_func_dict={"对对联:":self.playCouple,
                                        "对对联：":self.playCouple,
                                        "天气":self.weather,
                                        "暂停":self.pause,
                                        "重启":self.restart,
                                        }
        group=config.get("group")
        if(group==None):
            raise qqBotException("配置文件-group字段格式错误")
        if(not(str(group_id) in group)):
            raise qqBotException("群号"+str(group_id)+"未在配置文件中定义")
        self.group_id=group_id
        self.group_config=group.get(str(self.group_id))
        self.saveFlag=self.group_config.get("saveFlag")
        if(self.saveFlag==None):
            raise qqBotException("配置文件-saveFlag字段格式不正确！")
        self.pauseFlag=self.group_config.get("pauseFlag")
        if (self.pauseFlag == None):
            raise qqBotException("配置文件-pauseFlag字段格式不正确！")
        self.sendUrl=config.get("sendUrl")
        if(self.sendUrl==None):
            raise qqBotException("配置文件-sendUrl字段格式错误")
        self.gif_buffer=[]
    def send_group_msg(self,message,auto_escape=False):     #发送群消息
        data = {
            'group_id':self.group_id ,
            'message': message,
            'auto_escape': auto_escape
        }
        requests.post(self.sendUrl+"/send_group_msg",data=data)

    def set_group_kick(self,qqNumber,reject_add_request=False):     #reject_add_request  是否拒绝加群申请
        data = {
            'group_id': self.group_id,
            'user_id': qqNumber,
            'reject_add_request': reject_add_request
        }
        requests.post(self.sendUrl + "/set_group_kick", data=data)

    def set_group_ban(self,qqNumber,timeLength):              #单人禁言
        data = {
            'group_id': self.group_id,
            'user_id': qqNumber,
            'duration':timeLength            #秒
        }
        requests.post(self.sendUrl + "/set_group_ban", data=data)

    def set_group_anonymous_ban(self,anonymous,timeLength):   #匿名禁言
        data = {
            'group_id': self.group_id,
            'anonymous': qqNumber,
            'duration': timeLength  # 秒
        }
        requests.post(self.sendUrl + "/set_group_anonymous_ban", data=data)

    def set_group_whole_ban(self,enable=True):         #全体禁言
        data = {
            'group_id': self.group_id,
            'enable':enable          #是否全体禁言
        }
        requests.post(self.sendUrl + "/set_group_whole_ban", data=data)
    def set_group_anonymous(self,enable):       #是否允许匿名
        data = {
            'group_id': self.group_id,
            'enable': enable  # 是否允许
        }
        requests.post(self.sendUrl + "/set_group_anonymous", data=data)

    def set_group_special_title(self,user_id,special_title=''):
        data = {
            'group_id': self.group_id,
            'enable': enable,  # 是否允许
            'user_id':user_id,
            'special_title':special_title,
            'duration':-1
        }
        requests.post(self.sendUrl + "/set_group_special_title", data=data)

    def group_message_handle(self,data):
        if(self.saveFlag):     #是否存储聊天记录
            self.chatSave(data)
        #检测是否有AT
        data_bag = {
            'message': data.get('message'),
            'user_id': data.get('user_id')
        }
        if(self._AT(data_bag)):
            return
    def _AT(self,data_bag):
        AT_header='\[CQ:at,qq='+str(self.myQQ)+'\]'
        AT_state=re.match(AT_header,data_bag.get("message"))
        if(AT_state==None):
            return False
        for i in self.str_func_dict:
            re_se=re.search(i, data_bag.get("message"))
            if(re_se!=None):
                #检测是否为管理员暂停或者重启
                if(i=="暂停" or i=="重启"):
                    if(data_bag.get("user_id") in self.group_config.get("superUser")):
                        self.str_func_dict[i]()
                        break
                if(not self.pauseFlag):
                    data_bag["lastCharPosition"]=re_se.span()[1]
                    func=self.str_func_dict[i]
                    func(data_bag)
                    break
    def pause(self):
        self.pauseFlag=True
        self.send_group_msg("水群机器人暂停！")
    def restart(self):
        self.pauseFlag=False
        self.send_group_msg("水群机器人启动！")
    def chatSave(self,data):
        try:
            with open(self.group_config.get("savePath"),'a') as filePtr:
                filePtr.write("\n"+json.dumps(data))
        except Exception as e:
            print(e)
            raise qqBotException("不正确的聊天记录文件路径！")
    def playCouple(self,data_bag):
        upCoupleStr=data_bag.get("message")[data_bag.get("lastCharPosition"):]
        res_str=requests.get('https://ai-backend.binwang.me/chat/couplet/'+upCoupleStr).text
        downCoupleStr=json.loads(res_str).get('output')
        if(downCoupleStr==None or downCoupleStr==""):
            downCoupleStr="对联格式不正确！"
        self.send_group_msg(downCoupleStr)
    def gif(self,data_bag):
        if(len(self.gif_buffer)==0):
            pass
            #更新buffer
    def weather(self,data_bag):
        r = requests.get('http://www.weather.com.cn/data/sk/101043700.html')  # 获取
        r.encoding = 'utf-8'  # 编码
        str1="地区:" + r.json()['weatherinfo']['city']+"\n温度:" + r.json()['weatherinfo']['temp']+"\n湿度:" + r.json()['weatherinfo']['SD']
        self.send_group_msg(str1)
def route_by_message(data):  # 数据分类与分配函数
    if (data.get("message_type") == 'group'):
        group_dict[str(data.get("group_id"))].group_message_handle(data)


if(__name__=="__main__"):
    group_dict={}
    config=Config()
    bot_server = Flask(__name__)
    temp_group=config.get("group")
    for i in temp_group:
        group_dict[str(i)] = Group(int(i),config)
    '''信息接收'''
    @bot_server.route('/api/message', methods=['POST'])
    def server():
        data = request.get_data().decode('utf-8')
        data = json.loads(data)
        route_by_message(data)
        print(data)
        return ''
    bot_server.run(port=config.get("port"))


