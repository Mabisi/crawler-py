# -*- coding=utf-8 -*-
"""
tumblr多线程下载脚本。
feature：
1. 支持下载多个用户视频
2. 多线程下载
3. 自动去重已失效视频

 - 兼容Python2.7以上版本
 - windows下的兼容性未测试

- 安装依赖包：
pip install requests

- 修改脚本最后的tumblr用户名列表。
示例：
names=['username1','username2']

- 运行脚本
python tumblr.py
"""

from threading import Thread
import requests
import re
import os
import sys
if sys.version_info[0]==2:
    py3=False
    import Queue
else:
    py3=True
    import queue as Queue
import time

download_path='/root/tumblr/download'
if not os.path.exists(download_path):
    os.mkdir(download_path)
link_path='/root/tumblr/jiexi'
if not os.path.exists(link_path):
    os.mkdir(link_path)

api_url='http://%s.tumblr.com/api/read?&num=50&start='
UQueue=Queue.Queue()
def getpost(uid,queue):
    url='http://%s.tumblr.com/api/read?&num=50'%uid
    page=requests.get(url).text
    try:
        total=re.findall('<posts start="0" total="(.*?)">',page)[0]
        total=int(total)
        a=[i*50 for i in range(1000) if i*50-total<0]
        ul=api_url%uid
        for i in a:
            queue.put(ul+str(i))
    except Exception as e:
        print(u'geting posts from {} error:{}'.format(uid,e))
        return False


extractpicre = re.compile(r'(?<=<photo-url max-width="1280">).+?(?=</photo-url>)',flags=re.S)   #search for url of maxium size of a picture, which starts with '<photo-url max-width="1280">' and ends with '</photo-url>'
extractvideore=re.compile('/tumblr_(.*?)" type="video/mp4"')

video_links = []
pic_links = []
vhead = 'https://vt.tumblr.com/tumblr_%s.mp4'

class Consumer(Thread):
    def __init__(self, l_queue):
        super(Consumer,self).__init__()
        self.queue = l_queue

    def run(self):
        session = requests.Session()
        while 1:
            link = self.queue.get()
            print('start parse post: ' + link)
            try:
                content = session.get(link).text
                videos = extractvideore.findall(content)
                video_links.extend([vhead % v for v in videos])
                pic_links.extend(extractpicre.findall(content))
            except:
                print('url: %s parse failed\n' % link)
            if self.queue.empty():
                break


class Downloader(Thread):
    """docstring for Downloader"""
    def __init__(self, queue):
        super(Downloader, self).__init__()
        self.queue = queue

    def run(self):
        while 1:
            info=self.queue.get()
            url=info['url']
            path=info['path']
            try:
                r=requests.get(url,stream=True)
                with open(path,'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                print(u'download {} success'.format(path))
            except:
                print(u'download {} fail'.format(path))
            if self.queue.empty():
                break

def write(name):
    videos=list(set([i.replace('/480','').replace('.mp4.mp4','.mp4') for i in video_links]))
    pictures=list(set(pic_links))
    pic_path=os.path.join(link_path,'%s_pictures.txt'%name)
    vid_path=os.path.join(link_path,'%s_videos.txt'%name)
    with open(pic_path,'w') as f:
        for i in pictures:
            f.write('%s\n'%i)
    with open(vid_path,'w') as f:
        for i in videos:
            f.write('%s\n'%i)

def download_from_text(name,d_type):
    if d_type=='0':
        print(u"无需下载")
    elif d_type=='1':
        pic_path=os.path.join(link_path,'%s_pictures.txt'%name)
        vid_path=os.path.join(link_path,'%s_videos.txt'%name)
        print(u'开始下载视频')
        download(name,vid_path)
        print(u'开始下载图片')
        download(name,pic_path)
    elif d_type=='2':
        vid_path=os.path.join(link_path,'%s_videos.txt'%name)
        print(u'开始下载视频')
        download(name,vid_path)
    else:
        pic_path=os.path.join(link_path,'%s_pictures.txt'%name)
        print(u'开始下载图片')
        download(name,pic_path)


def download(username,filename,thread_num=10,threshold=1000):
    type_=re.findall('([^/]*?)_(pictures|videos)\.txt',filename)[0][1]
    queue=Queue.Queue()
    u_path=os.path.join(download_path,username)
    r_path=os.path.join(u_path,type_)
    if not os.path.exists(u_path):
        os.mkdir(u_path)
    if not os.path.exists(r_path):
        os.mkdir(r_path)
    with open(filename) as f:
        links=[i.strip() for i in f.readlines()]
    for link in links:
        name=os.path.basename(link)
        filepath=os.path.join(r_path,name)
        if not os.path.exists(filepath):
            queue.put(dict(url=link,path=filepath))
    ###download
    tasks=[]
    for i in range(min(thread_num,queue.qsize())):
        t=Downloader(queue)
        t.start()
        tasks.append(t)
    for t in tasks:
        t.join()
    ##remove invalid video
    invalidno=0
    files=[os.path.join(r_path,i) for i in os.listdir(r_path)]
    for file in files:
        if os.path.getsize(file)<=threshold:
            os.remove(file)
            invalidno+=1
    print(u'从 {} 删除 {} 个 大小小于 {}kb的文件'.format(r_path,invalidno,threshold))


def main(names):
    print(u"解析完毕后是否下载？\n 0. 不下载; 1. 全部下载； 2. 仅下载视频； 3. 仅下载图片")
    if py3:
        d_type=input()
    else:
        d_type=raw_input()
    for name in names:
        a=getpost(name,UQueue)
        if a!=False:
            task=[]
            for i in range(min(10,UQueue.qsize())):
                t=Consumer(UQueue)
                t.start()
                task.append(t)
            for t in task:
                t.join()
            write(name)
            print(u"解析完毕，请查看同目录下的文件")
            ##下载
            download_from_text(name,d_type)



if __name__=='__main__':
    names=['wanimal1983','xiaoqingqu'] #需下载的tumblr用户名列表
    main(names)


