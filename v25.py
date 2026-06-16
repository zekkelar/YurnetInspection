#!/usr/bin/env python3
# SHADOW CORE - UNLOCKED VERSION
# No license, no limits, no bullshit
# Made by STANLEY - FAC 2015

import requests, json
import base64 
import random
import time
from colorama import init, Fore, Back, Style
import sys
import argparse
import platform, uuid, hashlib, os
import requests
import json

biru = Fore.CYAN
kuning = Fore.YELLOW
reset = Style.RESET_ALL
hijau = Fore.GREEN

init(autoreset=True)

sesi = requests.Session()

class login:
    def __init__(self):
        self.url = "http://192.168.152.50:9004"
        self.sessionID="/Permission/GetSessionID"
        self.headers = {
            "User-Agent": "Dart/3.0 (dart:io)",
            "Accept-Encoding": "gzip",
            "Host": "192.168.152.50:9004"
        }
        self.idcard = "F10235721"
        self.msg = False

    def getSessionID(self):
        a = sesi.get(self.url+self.sessionID, headers=self.headers, verify=False, timeout=10)
        if self.msg:
            print(a.text)
        getJson = json.loads(a.text)
        sessionID = getJson["Data"]
        newdata = f"sessionID={sessionID}&v=0.9343335479497862"
        sample_string = newdata
        sample_string_bytes = sample_string.encode("ascii")
        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string = base64_bytes.decode("ascii")
        print(f'[?] new Data: {newdata}')
        print(f"[!] Encoded string: {base64_string}")
        return base64_string, sessionID

    def getCaptcha(self, paramSessionID):
        url = self.url+"/Permission/GetValidateCode?"+paramSessionID
        b = sesi.get(url, headers=self.headers, verify=False, timeout=10)        
        with open("captcha.png" , "wb") as f:
            f.write(b.content)
        print('[!] Captcha saved as captcha.png')

    def Log(self, sessionID):
        ask = input("captcha : ")
        url = self.url+"/Permission/MesUserLogin"
        headers2= {
            "user-agent": "Dart/3.0 (dart:io)",
            "content-type": "application/json",
            "accept-encoding": "gzip",
            "sessionid": sessionID,
            "host": "192.168.152.50:9004"
        }
        data={"UserAccount":self.idcard,"UserPwd":"f7b186cbcc32368ae49a9d1c52bbcabe","UniqueCode":"","SourceType":"app","VerificationCode":int(ask)}
        c = requests.post(url,headers=headers2, json=data, verify=False)
        if self.msg:
            print(c.status_code)
            print(c.headers)
            print(c.text)
        stat = json.loads(c.text)
        if stat['Message'] == 1:
            print(f'[!] Login Success as {self.idcard}')
            print(f'[!] SessionID : {sessionID}')
            return sessionID

    def main(self):
        paramSessionID, sessionID = self.getSessionID()
        self.getCaptcha(paramSessionID)
        return self.Log(sessionID)


class newinspeksi:
    def __init__(self, msg=False, randomDelay=True, electricalOnly=False, 
                    unitElectrical=False, unittest=False, user=False, unit=False,
                    OnlyESP=False, unittestv2=False, exceptual=False, slow=False):

        with open('user.json', 'r', encoding='utf-8') as file:
            self.user = json.loads(file.read())
        self.basicAuth = open('auth.txt', 'r', encoding='utf-8').read().splitlines()[0]
        self.url = "http://192.168.152.50:9004"
        self.headers = {
            "User-Agent": "Dart/3.0 (dart:io)",
            "Accept-Encoding": "gzip",
            "Authorization": "BasicAuth "+self.basicAuth,
            "Host": "192.168.152.50:9004",
        }
        self.inspeksidata = []
        self.msg = msg
        self.randomDelay = randomDelay
        self.random_delay = [178, 124, 177, 166, 134, 146, 173, 127, 138, 162, 127, 122, 150, 171, 151, 179, 156, 164, 165, 136]
        self.unittest = unittest
        self.unittestv2=unittestv2
        self.slow = slow
        self.selectedUser = user 
        self.selectedUnit = unit
        self.exceptual = []
        if exceptual:self.exceptual = exceptual.split(',')
        print(f'{self.get_time()} [{kuning}WARNING{reset}] Unit Test: {unittest}')

        print(f"""
Slow : {self.slow}
Exceptual: {self.exceptual}
User : {self.selectedUser}
Unit : {self.selectedUnit}
        """)

        if electricalOnly:
            print(f'{self.get_time()} [{kuning}WARNING{reset}] Active Electrical Inspection Only !!')
            with open('electric.json', 'r', encoding='utf-8') as file:
                self.unit = json.loads(file.read())

        elif OnlyESP:
            print(f'{self.get_time()} [{kuning}WARNING{reset}] Active ESP Inspection!!')
            with open('esp.json', 'r', encoding='utf-8') as file:
                self.unit = json.loads(file.read())

        elif unitElectrical:
            print(f'{self.get_time()} [{kuning}WARNING{reset}] Active Inspection with Electrical Tienji walawala !!')
            with open('unitElectrical.json', 'r', encoding='utf-8') as file:
                self.unit = json.loads(file.read())
        else:
            with open('unit.json', 'r', encoding='utf-8') as file:
                self.unit = json.loads(file.read())

        with open('electric.json', 'r', encoding='utf-8') as file:
            self.elektrik = json.loads(file.read())

    def paramEncoding(self, id, nfccode):
        param = f"iCurPage=1&iPageRowNum=20&sWhere=InspectionStatus in('1', '4') and (GroupCode in ('Group_2023071900001') and (InspectionPeople is null or InspectionPeople='')  or CHARINDEX('{id}',InspectionPeople)>0) and NFCCode='{nfccode}'&sOrder=PointNo&queryName=&sTopNum=1&draw="
        sample_string = param
        sample_string_bytes = sample_string.encode("ascii")
        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string = base64_bytes.decode("ascii")
        return base64_string

    def getWorkOrder(self, encodedparam=None):
        param = "/UnInspectionPoint/QueryAPP?"+encodedparam
        src = requests.get(self.url+param, headers=self.headers, verify=False, timeout=7).text
        if self.msg:
            print(src)
        parseData = json.loads(src)

        if parseData["total"]>0:
            for x in parseData["rows"]:
                return x["WorkOrderCode"], x["PointCode"]
        elif parseData["total"]==0:
            return None, None
        elif(parseData["Message"]) == "Authorization has been denied for this request.":
            return 406, 406
        else:
            return None, None

    def getID(self, workOrderCode, PointCode, ids, name):
        param = f"iCurPage=1&iPageRowNum=0&sWhere=WorkOrderCode='{workOrderCode}' and PointCode='{PointCode}'&sOrder=EquipmentCode&queryName=&sTopNum=1&draw=1"
        sample_string = param
        sample_string_bytes = sample_string.encode("ascii")
        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string = base64_bytes.decode("ascii")
        param = "/InspectionItem/QueryApp?"+str(base64_string)
        src = requests.get(self.url+param, headers=self.headers, verify=False, timeout=7).text 
        if self.msg:
            print(src)
        parseData = json.loads(src)
        ms = random.randint(1000,5000)
        for x in parseData["rows"]:
            param = {"ID":x["ID"],
                     "WorkOrderCode":f"{workOrderCode}","PointCode":f"{PointCode}",
                     "EquipmentCode":f"{x['EquipmentCode']}","UseMilliseconds":ms,
                     "ActuralValue":"","Result":"1","DefectRemark":"","DefectType":"",
                     "DefectTypeName":"","ActuralPerson":f"{ids}","ActuralPersonName":f"{name}",
                     "AnnixFlag":"0","EquipmentStatusCode":"EM_YX","EquipmentStatusName":"",
                     "AppendixList":[],"PhotoList":[],"TakePhotoTime":""}
            self.inspeksidata.append(param)

    def inspeksi(self):
        models = {'models':(None,json.dumps(self.inspeksidata), "application/json")}
        src = requests.post(self.url+"/InspectionOrder/Commit", files=models, verify=False, headers=self.headers, timeout=7) 
        if self.msg:
            print(src.text)
        parse = json.loads(src.text)
        if parse['Result'] == True:
            print(f'{self.get_time()} {self.info()} Inspeksi Success')
        else:
            print(f'{self.get_time()} {self.info()} Inspeksi Failed')

    def banner(self):
        for x in self.user:
            print(f'[{x}] {self.user[x]["name"]} [{kuning}{self.user[x]["status"].upper()}{reset}]')

    def banner_alat(self, selectedunit):
        for x in self.unit[selectedunit]:
            print(f'[{x}] {self.unit[selectedunit][x]["PointName"]}')

    def banner_unit(self):
        print("""
[1] Unit 1
[2] Unit 2
[3] Unit 3
[4] Unit 4
[5] Unit 5
            """)
    def banner_esp(self):
        print("""
[1] Unit 1
[3] Unit 3
[5] Unit 5
            """)

    def main(self):
        while True:
            self.inspeksidata.clear()
            self.banner()
            print('')
            selectedUser = int(input('User : '))
            self.banner_unit()
            print('')
            selectedUnit = (input('Unit: '))
            self.banner_alat(selectedUnit)
            selectedPoint = (input('Inspeksi No : '))
            print('')
            param = self.paramEncoding(self.user[f'{selectedUser}']['id'], self.unit[selectedUnit][selectedPoint]['NFCCode'])
            WorkOrderCode, PointCode = self.getWorkOrder(encodedparam=param)
            if WorkOrderCode == None:
                print('[!] Sudah di inspeksikannya bujang')
            elif WorkOrderCode == 406:
                ask = input ('[!] Login ulang, y/n ? ')
                if ask == 'y':
                    log = login()
                    sessionid = log.main()
                    open('auth.txt', 'w', encoding='utf-8').write(sessionid)
                    print('[~] Login success')
                    print('[!] Try to inspection again sir')
                else:
                    exit()
            else:
                if self.unittest:
                    print('[+] Unit test, Meyou Inspeksi')
                else:
                    self.getID(WorkOrderCode, PointCode, self.user[f'{selectedUser}']['id'], self.user[f'{selectedUser}']['name'])
                    print("hanya test")
                    #self.inspeksi()
            
            lanjut = input('lnjut? ')
            if lanjut == '':
                pass 
            else:
                break
    
    def hitung_mundur(self, delay):
        for i in range(delay, 0, -1):
            print(f"{self.get_time()} {self.info()} Countdown: {i} seconds remaining", end="\r")
            time.sleep(1)

    def generate_random_delays(self,num_delays, a, b):
        delays = []
        for _ in range(num_delays):
            delay = random.randint(a, b)
            delays.append(delay)
        return delays

    def get_time(self):
        return time.strftime(f"[{biru}%H:%M:%S{reset}]")

    def info(self):
        return f"[{hijau}INFO{reset}]"

    def automatic(self, msg=True):
        self.msg = msg
        print(f'{self.get_time()} {self.info()} Show Message : {self.msg}')
        print('')

        self.inspeksidata.clear()
        self.banner()

        if self.selectedUser == False:
            print('')
            selectedUser = int(input('User : '))
            self.banner_unit()
            print('')
            selectedUnit = (input('Unit: '))
        else:
            selectedUser = self.selectedUser
            selectedUnit = str(self.selectedUnit)

        proses_berjalan = 0 
        untuk_exceptual = 1
        try:
            a=self.unit[str(selectedUnit)]
        except KeyError:
            print(f'[{kuning}WARNING{reset}] Unit tidak tersedia !')
            exit()

        for InspeksiPoint in self.unit[str(selectedUnit)]:
            self.inspeksidata.clear()
            if self.unittestv2:
                name = (self.unit[selectedUnit][InspeksiPoint]['PointName'])
                nfccode = (self.unit[selectedUnit][InspeksiPoint]['NFCCode'])
                routecode = (self.unit[selectedUnit][InspeksiPoint]['RouteName'])
                print(f"{self.get_time()} {self.info()} Point : {name}")
                print(f'{self.get_time()} {self.info()} Routename : {routecode}')
                print(f"{self.get_time()} {self.info()} Unit : {selectedUnit}")
                print(f"{self.get_time()} {self.info()} People : {self.user[f'{selectedUser}']['name']}")
                print(f"{self.get_time()} {self.info()} [UNIT TEST]")
                print("")
            else:
                print("")
                
                name = (self.unit[selectedUnit][InspeksiPoint]['PointName'])
                nfccode = (self.unit[selectedUnit][InspeksiPoint]['NFCCode'])
                routecode = (self.unit[selectedUnit][InspeksiPoint]['RouteName'])
                print(f"{self.get_time()} {self.info()} Point : {name}")
                print(f'{self.get_time()} {self.info()} Routename : {routecode}')
                print(f"{self.get_time()} {self.info()} Unit : {selectedUnit}")
                print(f"{self.get_time()} {self.info()} People : {self.user[f'{selectedUser}']['name']}")

                if str(untuk_exceptual) in self.exceptual:
                    print(f"{self.get_time()} {self.info()} {kuning}INFO : SKIPPED: Exceptual{reset}")
                else:
                    WorkOrderCode, PointCode = self.before_inspect(selectedUser, nfccode)

                    if WorkOrderCode == 0:
                        print(f'{self.get_time()} {self.info()} Sudah di inspeksikannya bujang')

                    elif WorkOrderCode == 406:
                        ask = input ('[!] Login ulang, y/n ? ')
                        if ask == 'y':
                            log = login()
                            sessionid = log.main()
                            open('auth.txt', 'w', encoding='utf-8').write(sessionid)
                            print('[~] Login success')
                            print('[!] Try to inspection again sir')
                        else:
                            exit()
                    else:
                        if self.slow:
                            delay = self.slow_living(name)
                        else:
                            delay = self.fast_living(name)
                        if proses_berjalan != 0:
                            print(f'{self.get_time()} Waiting Delay: {delay} Second')
                            self.hitung_mundur(delay)
                        print(f'{self.get_time()} {self.info()} Get ID ... ')

                        self.inspect(WorkOrderCode, PointCode, self.user[f'{selectedUser}']['id'], self.user[f'{selectedUser}']['name'])
                    
                        self.inspeksidata.clear()
                        proses_berjalan+=1
                untuk_exceptual += 1

    def slow_living(self, name):
        if name == "直流配电室DC distribution room":
            delay = random.choice(self.generate_random_delays(20, 25, 30))                    
        elif "protection room" in name:
            delay = random.choice(self.generate_random_delays(30, 50, 60))
        elif name=="400V配电室400V distribution room":
            delay = random.choice(self.generate_random_delays(10, 20, 30))
        elif name=="左侧给煤机平台 left coal feeder platform":
            delay = random.choice(self.generate_random_delays(20, 25, 32))
        elif "Generator outlet" in name:
            delay = random.choice(self.generate_random_delays(50, 55, 62))    
        elif name=="发电机、封母Generator, seal":
            delay = random.choice(self.generate_random_delays(15, 17, 19))    
        elif name=="保安柴发配电室Security diesel generator power distribution room":
            delay = random.choice(self.generate_random_delays(40, 52, 63))    
        elif "Dust removal distribution room" in name:    
            delay = random.choice(self.generate_random_delays(300, 290, 320))    
        else:                    
            delay = random.choice(self.random_delay)
        return delay

    def fast_living(self, name):
        if name == "直流配电室DC distribution room":
            delay = random.choice(self.generate_random_delays(20, 25, 30))                    
        elif "protection room" in name:
            delay = random.choice(self.generate_random_delays(30, 50, 60))
        elif name=="400V配电室400V distribution room":
            delay = random.choice(self.generate_random_delays(10, 20, 30))
        elif name=="左侧给煤机平台 left coal feeder platform":
            delay = random.choice(self.generate_random_delays(20, 25, 32))
        elif "Generator outlet" in name:
            delay = random.choice(self.generate_random_delays(50, 55, 62))    
        elif name=="发电机、封母Generator, seal":
            delay = random.choice(self.generate_random_delays(15, 17, 19))    
        elif name=="三台流化风 机 three fluidizing fans":
            delay = random.choice(self.generate_random_delays(30, 45, 50))    
        elif name=="底渣系统 Boiler Ash Conveying System":
            delay = random.choice(self.generate_random_delays(20, 26, 30))            
        elif name=="B侧一、二次风机 B side Primary fans and secondary fan":
            delay = random.choice(self.generate_random_delays(30, 38, 49))                
        elif name=="10kV配电室10kV distribution room":
            delay = random.choice(self.generate_random_delays(40, 60, 62))    
        elif name=="保安柴发配电室Security diesel generator power distribution room":
            delay = random.choice(self.generate_random_delays(40, 52, 63))    
        elif "Dust removal distribution room" in name:    
            delay = random.choice(self.generate_random_delays(300, 290, 320))    
        else:                    
            delay = random.choice(self.random_delay)
        return delay

    def before_inspect(self, selectedUser, nfccode):
        try:
            print(f'{self.get_time()} {self.info()} Encoding parameter...')
            param = self.paramEncoding(self.user[f'{selectedUser}']['id'], nfccode)
            print(f'{self.get_time()} {self.info()} Getting Work Order .... ')
            WorkOrderCode, PointCode = self.getWorkOrder(encodedparam=param)
            if WorkOrderCode == None:
                WorkOrderCode = 0
                PointCode = 0
            print(f'{self.get_time()} {self.info()} WC:{WorkOrderCode}|PC:{PointCode}')
            return WorkOrderCode, PointCode
        except Exception as e:
            print(f"{self.get_time()} [{kuning}WARNING{reset}] TRYING ERROR AT BEFORE INSPECT FUNCTION")
            time.sleep(2)
            return self.before_inspect(selectedUser, nfccode) 

    def inspect(self, WorkOrderCode, PointCode, userid, username):
        try:
            self.getID(WorkOrderCode, PointCode, userid, username)
            print(f'{self.get_time()} {self.info()} Process inspeksi...')
            if self.unittest:
                print(f'{self.get_time()} {self.info()} UNITTEST ')
            else:
                print('hanya test')
                #pass
                #self.inspeksi()
            print(f'{self.get_time()} {self.info()} Clear cache')
        except Exception as e:
            print(f"{self.get_time()} [{kuning}WARNING{reset}] Error jaringan, msg:")
            print(f"{self.get_time()} [{kuning}WARNING{reset}] MENCOBA NGULANG LAGI ADIKS")
            os.system("termux-toast ERROR COK INSPEKSINYA CEK CEK CEK CEK CEK CEK")
            time.sleep(3)
            self.inspect(WorkOrderCode, PointCode, userid, username)

    def elektrikal(self, msg=True):
        print("[~] Electrical Inspection Unit | HJF | Love HJF | Thankyou HollySys")
        self.msg = msg
        print(f"{self.get_time()} {self.info()} Show Message Info : {self.msg}")
        print("")
        self.inspeksidata.clear()
        self.banner()
        print('')

        print(f'Selected User: {self.selectedUser}')

        if self.selectedUser == False:
            print('')
            selectedUser = int(input('User : '))
            self.banner_unit()
            print('')
            selectedUnit = (input('Unit: '))
        else:
            selectedUser = self.selectedUser
            selectedUnit = '5'

        proses_berjalan = 0 

        for InspeksiPoint in self.elektrik[selectedUnit]:
            self.inspeksidata.clear()
            print("")

            if self.unittest:
                name = (self.elektrik[selectedUnit][InspeksiPoint]['PointName'])
                nfccode = (self.elektrik[selectedUnit][InspeksiPoint]['NFCCode'])
                routecode = (self.elektrik[selectedUnit][InspeksiPoint]['RouteName'])
                print(f"{self.get_time()} {self.info()} Point : {name}")
                print(f'{self.get_time()} {self.info()} Routename : {routecode}')
                print(f"{self.get_time()} {self.info()} Unit : {selectedUnit}")
                print(f"{self.get_time()} {self.info()} People : {self.user[f'{selectedUser}']['name']}")
                print(f"{self.get_time()} {self.info()} [UNIT TEST]")
                print("")
            else:
                name = (self.elektrik[selectedUnit][InspeksiPoint]['PointName'])
                nfccode = (self.elektrik[selectedUnit][InspeksiPoint]['NFCCode'])
                routecode = (self.elektrik[selectedUnit][InspeksiPoint]['RouteName'])
                print(f"{self.get_time()} {self.info()} Point : {name}")
                print(f'{self.get_time()} {self.info()} Routename : {routecode}')
                print(f"{self.get_time()} {self.info()} Unit : {selectedUnit}")
                print(f"{self.get_time()} {self.info()} People : {self.user[f'{selectedUser}']['name']}")

                print(f'{self.get_time()} {self.info()} Encoding parameter...')
                param = self.paramEncoding(self.user[f'{selectedUser}']['id'], nfccode)

                print(f'{self.get_time()} {self.info()} Getting Work Order .... ')
                WorkOrderCode, PointCode = self.getWorkOrder(encodedparam=param)
                if WorkOrderCode == None:
                    print(f'{self.get_time()} {self.info()} Sudah di inspeksikannya bujang')

                elif WorkOrderCode == 406:
                    ask = input ('[!] Login ulang, y/n ? ')
                    if ask == 'y':
                        log = login()
                        sessionid = log.main()
                        open('auth.txt', 'w', encoding='utf-8').write(sessionid)
                        print(f'{self.get_time()} {self.info()} Login success')
                        print(f'{self.get_time()} {self.info()} Try to inspection again sir')
                    else:
                        exit()
                else:
                    if "10kV" in name:
                        delay = random.choice(self.generate_random_delays(10, 30, 40))
                    if "400V" in name:
                        delay = random.choice(self.generate_random_delays(10, 20, 30))
                    if "Generator outlet" in name:
                        delay = random.choice(self.generate_random_delays(10, 30, 40))
                    if "DC distribution room" in name:
                        delay = random.choice(self.generate_random_delays(10, 30, 40))                                
                    else:                    
                        delay = random.choice(self.random_delay)

                    if proses_berjalan != 0:
                        print(f'{self.get_time()} {self.info()} Waiting Delay: {delay} Second')
                        self.hitung_mundur(delay)
                    print(f'{self.get_time()} {self.info()} Get ID ... ')
                    try:
                        self.getID(WorkOrderCode, PointCode, self.user[f'{selectedUser}']['id'], self.user[f'{selectedUser}']['name'])
                        print(f'{self.get_time()} {self.info()} Process inspeksi...')
                        if self.unittest:
                            print('unittest')
                        else:
                            print("Hanya test")
                            pass
                        print(f'{self.get_time()} {self.info()} Clear cache')
                    except Exception as e:
                        print(f"{self.get_time()} [{kuning}WARNING{reset}] Error jaringan, msg:")
                        break
        
                    self.inspeksidata.clear()
                proses_berjalan+=1


class AddUser:
    def __init__(self):
        pass

    def load_from_json(self, filename='user.json'):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def add_user(self, data_dict, user_id, user_name, status='active'):
        if data_dict:
            last_key = max([int(k) for k in data_dict.keys() if k.isdigit()], default=0)
            new_key = str(last_key + 1)
        else:
            new_key = '1'
        
        new_user = {
            "id": user_id,
            "name": user_name,
            "status": status
        }
        data_dict[new_key] = new_user
        return new_key

    def save_to_json(self, data_dict, filename='user.json'):
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data_dict, file, indent=4, ensure_ascii=False)
    
    def delete_user(self, data_dict, key):
        if key in data_dict:
            del data_dict[key]
            return True
        return False
    
    def list_users(self, data_dict):
        result = []
        for key, val in sorted(data_dict.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            result.append({
                'key': key,
                'id': val.get('id', '-'),
                'name': val.get('name', '-'),
                'status': val.get('status', 'active')
            })
        return result


def bannernjir():
    print("""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ┳┳┓┏┓┏┓  ┏┓┏┳┓┏┓┳┓┓ ┏┓┓┏ ┃
┃ ┃┃┃┣ ┗┓  ┗┓ ┃ ┣┫┃┃┃ ┣ ┗┫ ┃
┃ ┛ ┗┗┛┗┛  ┗┛ ┻ ┛┗┛┗┗┛┗┛┗┛ ┃                       
┃ [*] Inspeksi from Mess   ┃
┃ [!] cOder : STANLEY      ┃ 
┃ [!] Version : UNLOCKED   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        """)

def get_time():
    return time.strftime(f"[{biru}%H:%M:%S{reset}]")


def checking():
    url = "http://192.168.152.50:9004"
    headers = {"User-Agent": "Dart/3.0 (dart:io)",
            "Accept-Encoding": "gzip",
            "Host": "192.168.152.50:9004"}
    
    try:
        print(f'{get_time()} [{hijau}INFO{reset}] Checking connection to HollySys Server...')
        a = sesi.get(url, headers=headers, verify=False, timeout=10)
        print(f'{get_time()} [{hijau}INFO{reset}] Connected!')
        return True
    except Exception as e:
        print(e)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SHADOW CORE - UNLOCKED')
    parser.add_argument("-electrical", action="store_true", help="Only electrical inspection")
    parser.add_argument("-auto", action="store_true", help="Automatic Inspection")
    parser.add_argument("-msg", action="store_true", help="If u wanna show message server")
    parser.add_argument("-adduser", action="store_true", help='Add new user')
    parser.add_argument("-login", action="store_true", help='new login')
    parser.add_argument("-ie", action="store_true", help='Electrical Inspection all unit')
    parser.add_argument("-unitElectrical", action="store_true", help='Inspection with electrical')
    parser.add_argument("-unittest", action="store_true", help="Test mode")
    parser.add_argument("-changeServer", action="store_true", help="Change server")
    parser.add_argument("-stan", action="store_true", help="Developer mode")
    parser.add_argument("-esp", action="store_true", help="ESP inspection")
    parser.add_argument("-unittestv2", action="store_true", help="Test mode v2")
    parser.add_argument("-unit", type=int, help='Unit number')
    parser.add_argument("-user", type=int, help='User')
    parser.add_argument("-exceptual", type=str, help="Skip list")
    parser.add_argument("-slow", action='store_true', help='Slow mode')
    parser.add_argument("-listunit", action="store_true", help="List units")
    
    args = parser.parse_args()
    
    bannernjir()
    print(f"{get_time()} [{hijau}UNLOCKED{reset}] No license required - FREE FOREVER")
    print("")
    
    # Connection check to HollySys server
    if not checking():
        print(f"{get_time()} [{kuning}WARNING{reset}] Cannot connect to HollySys server!")
        print(f"{get_time()} [{kuning}WARNING{reset}] Check network connection or server status")
        sys.exit(1)
    
    print(f"{get_time()} [{hijau}INFO{reset}] Connected to HollySys server")
    print("")
    
    # Handle adduser command
    if args.adduser:
        run = AddUser()
        data = run.load_from_json()
        
        print("\n" + "="*50)
        print("  ADD NEW USER")
        print("="*50)
        
        if data:
            print("\nExisting users:")
            for key, val in data.items():
                print(f"  [{key}] {val.get('name', '-')} (ID: {val.get('id', '-')})")
        else:
            print("\nNo existing users")
        
        print("\n" + "-"*50)
        new_id = input("Masukkan ID pengguna baru: ").strip()
        new_name = input("Masukkan nama pengguna baru: ").strip()
        
        if not new_id or not new_name:
            print("[!] ID dan nama tidak boleh kosong!")
            sys.exit(1)
        
        for key, val in data.items():
            if val.get('id') == new_id:
                print(f"[!] ID {new_id} sudah digunakan oleh {val.get('name')}")
                sys.exit(1)
        
        run.add_user(data, new_id, new_name)
        run.save_to_json(data)
        
        print(f"\n[✓] User added successfully!")
        print(f"    ID: {new_id}")
        print(f"    Name: {new_name}")
        print("="*50)
        sys.exit(0)
    
    # Handle login command
    if args.login:
        log = login()
        sessionid = log.main()
        with open('auth.txt', 'w', encoding='utf-8') as f:
            f.write(sessionid)
        print(f"{get_time()} [{hijau}INFO{reset}] Login success, session saved")
        sys.exit(0)
    
    # Handle listunit command
    if args.listunit:
        print("\n" + "="*65)
        print(f"{biru}  UNIT LIST{reset}")
        print("="*65)
        
        json_file = 'unitElectrical.json'
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for unit in sorted(data.keys(), key=int):
                print(f"  Unit {unit}: {len(data[unit])} points")
        else:
            print("  unitElectrical.json not found")
        print("="*65)
        sys.exit(0)
    
    # Handle automatic inspection
    if args.auto:
        new = newinspeksi(
            OnlyESP=args.esp,
            electricalOnly=args.electrical,
            unitElectrical=args.unitElectrical,
            unittest=args.unittest,
            unit=args.unit,
            user=args.user,
            unittestv2=args.unittestv2,
            exceptual=args.exceptual,
            slow=args.slow
        )
        new.automatic(msg=args.msg)
        sys.exit(0)
    
    # Handle electrical inspection
    if args.ie:
        new = newinspeksi(
            unit=args.unit,
            user=args.user,
            unittest=args.unittest
        )
        new.elektrikal(msg=args.msg)
        sys.exit(0)
    
    # Default interactive mode
    new = newinspeksi()
    new.main()