from flask import Flask, flash, redirect, render_template, request, session, abort
from random import randint
from werkzeug.utils import secure_filename
from helpers import *
import MongoDatabase

app = Flask(__name__)
app.config.from_object("config")
USER = ""
PATH = S3_BUCKET+" /"
folder_clicked = " "
objects = s3.list_objects(Bucket=S3_BUCKET)
file_names= [file["Key"] for file in objects["Contents"]]
currentFilter ="None"

@app.route("/",methods = ['GET','POST'])
def index():
	print(request.method)
	if request.method == 'GET':
		return render_template("user_login.html")
	elif request.method == 'POST':
		name = request.form["username"]
		print(name)
		global USER
		USER=name
		insert_user(USER)
		return redirect("/home")

@app.route("/home", methods=['GET', 'POST'])
def home():
	global PATH, folder_clicked
	PATH=S3_BUCKET+" / "
	folder_clicked=" "
	objects = s3.list_objects(Bucket=S3_BUCKET)
	file_names= [file["Key"] for file in objects["Contents"]]
	currentFilter ="None"
	return redirect("/gallery")

def allowed_file(filename):
	ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/forFolderslist", methods=['POST'])
def forFolderslist():
	global folder_clicked, PATH
	if request.method == 'POST':
		folder_clicked = request.form['folder_click']
		if folder_clicked is not None:
			PATH +=folder_clicked+" / "
		print(folder_clicked)
		return redirect("/gallery")

@app.route("/gallery", methods=['GET','POST'])
def gallery():
	global USER
	user=USER
	global PATH, file_names, folder_clicked, currentFilter
	path=PATH
	currFilter = currentFilter	
	# for POST request 
	if request.method == 'POST':
		file_name = request.form['rate_form_name']
		print(file_name)
		rating = request.form['rate_the_pic']
		rating = int(rating)
		pic_rating(file_name,rating)
		insert_user_rating(file_name, rating)
	files=[]
	folders=[]
	pics_with_ratings = {}
	s3_bucket=S3_BUCKET
	folders_count=0
	for item in file_names:
		splittedList = list(filter(None, item.strip().split("/")))
		if folder_clicked is not None and folder_clicked in splittedList:
			index = splittedList.index(folder_clicked)
			tmp_list = []
			for i in range(index+1, len(splittedList)):
				tmp_list.append(splittedList[i])
			splittedList = tmp_list
		if ("/" not in item and folder_clicked.__eq__(" ")):
			insert_pic(item)
			files.append(item)
			pics_with_ratings[item] = 0
		if ("/" in item and len(splittedList) == 1):
			if (item[-1] != '/'):
				files.append(item)
				print("+++++"+ item)
		if ("/" in item and len(splittedList) > 1):
			if splittedList[0] not in folders:
				folders.append(splittedList[0])
				folders_count += 1
	folders.extend(files)
	files_folders=folders
	db = MongoDatabase.config_mongodb()
	obj = db.user.find_one({"user":user})["pics_ratings"]
	for image in obj:
		pics_with_ratings[image[0]] = image[1]
	
	return render_template('/gallery_index.html', **locals()) 

def insert_user(user):
	db = MongoDatabase.config_mongodb()
	flag = db.user.find_one({"user": user})
	print(flag)
	print("**********************")
	if flag is None:
		user_doc = {}
		user_doc["user"] = user
		user_doc["pics_ratings"] = []
		db.user.insert(user_doc)
		print("user inserted in db")

def insert_user_rating(pic, rating):
	global USER
	if USER is not None:
		db = MongoDatabase.config_mongodb()
		obj = db.user.find_one({"user": USER})
		if obj is not None:
			picsList = obj["pics_ratings"]
			flag = False;
			print(picsList)
			for i in range(0, len(picsList)):
				if picsList[i][0].__eq__(pic):
					picsList[i][1] = rating
					flag = True
					break
			if (flag):
				db.user.update({"user" : USER}, {"$set":{"pics_ratings": picsList}})
				print("updated")
			else:
				db.user.update({"user" : USER}, {"$push":{"pics_ratings": [pic, rating]}})
				print("added")


def insert_pic(file_name):
	#print(file_name+"------------------------")
	db = MongoDatabase.config_mongodb()
	#print(db)
	flag = db.pics.find_one({"pic_id":file_name})
	#print(flag)
	if flag is None:
		pic_doc = {}
		rating_list = []
		pic_doc["pic_id"] = file_name
		pic_doc["rating_list"] = rating_list
		db.pics.insert(pic_doc)

def pic_rating(file_name,rating):
	db = MongoDatabase.config_mongodb()
	flag = db.pics.find_one({"pic_id":file_name})
	if flag is None:
		return {"status":"failed"}
	else:
		db.pics.update({"pic_id":file_name},{"$push":{"rating_list":rating}})

@app.route("/logout", methods=['POST'])
def logout():
	global USER, PATH, folder_clicked
	USER=""
	PATH=S3_BUCKET+"/"
	folder_clicked=" "
	return redirect("/")

@app.route("/ratingsfilter", methods=['GET','POST'])
def ratingsfilter():
	global USER, currentFilter, file_names
	user=USER
	allFiles=[]
	db = MongoDatabase.config_mongodb()
	if request.method == 'POST':
		filterRating = request.form.get('dropdown')
		obj = db.user.find_one({"user":user})["pics_ratings"]
		if len(filterRating) == 2:
			print("entered")
			if filterRating[0] is '>':
				print("started")
				for item in obj:
					if item[1] > int(filterRating[1]):
						allFiles.append(item[0])
			if filterRating[0] is '<':
				for item in obj:
					if item[1] < int(filterRating[1]):
						allFiles.append(item[0])
			if filterRating[0] is '=':
				for item in obj:
					if item[1] == int(filterRating[1]):
						allFiles.append(item[0])
			print(allFiles)
			file_names=allFiles
		if len(filterRating) > 2:
			objects = s3.list_objects(Bucket=S3_BUCKET)
			file_names= [file["Key"] for file in objects["Contents"]]
		currentFilter=filterRating
	return redirect("/gallery")

if __name__ == "__main__":
	app.run()
