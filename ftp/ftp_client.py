from ftplib import FTP

ftp = FTP('')
ftp.connect('localhost',1026)
ftp.login()
ftp.cwd('Desktop/websockets/ftp') #replace with your directory
ftp.retrlines('LIST')

def uploadFile():
    filename = 'target.mp4' #replace with your file in your home folder
    ftp.storbinary('STOR '+filename, open(filename, 'rb'))
    ftp.quit()

uploadFile()
