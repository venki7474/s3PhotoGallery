from flask import Flask, flash, redirect, render_template, request, session, abort
from random import randint
from werkzeug.utils import secure_filename
from helpers import *
import MongoDatabase

app = Flask(__name__)
app.config.from_object("config")
#global variable used throughout this app
USER = ""
PATH = S3_BUCKET+" /"
folderClicked = " "
objects = s3.list_objects(Bucket=S3_BUCKET)
filesToDisplay= [file["Key"] for file in objects["Contents"]]
currentFilter ="None"

# Index landing page
@app.route("/",methods = ['GET','POST'])
def index():
	#print(request.method)
	if request.method == 'GET':
		return render_template("user_login.html")
	elif request.method == 'POST':
		name = request.form["username"]
		global USER
		USER=name
		insert_user(USER)
		return redirect("/home")
# Landing page after entering name
@app.route("/home", methods=['GET', 'POST'])
def home():
	global PATH, folderClicked
	PATH=S3_BUCKET+" / "
	folderClicked=" "
	objects = s3.list_objects(Bucket=S3_BUCKET)
	filesToDisplay= [file["Key"] for file in objects["Contents"]]
	currentFilter ="None"
	return redirect("/gallery")

# when the subfolder is clicked this view is invoked
@app.route("/forFolderslist", methods=['POST'])
def forFolderslist():
	global folderClicked, PATH
	if request.method == 'POST':
		folderClicked = request.form['folder_click']
		if folderClicked is not None:
			# appending the path
			PATH +=folderClicked+" / "
		return redirect("/gallery")

# This is the main part of the application, it checks the user and takes all the files from S3 bucket and stores in the 
# mongoDB and the users and respective ratings are stored in mongoDB
# 
@app.route("/gallery", methods=['GET','POST'])
def gallery():
	global USER, PATH, filesToDisplay, folderClicked, currentFilter
	user=USER
	path=PATH
	currFilter = currentFilter	
	# for POST request of user rating
	if request.method == 'POST':
		fileName = request.form['rate_form_name']
		rating = request.form['rate_the_pic']
		rating = int(rating)
		# storing the rating with the user in the db
		pic_rating(fileName,rating)
		insert_user_rating(fileName, rating)
	files=[]
	folders=[]
	pics_with_ratings = {}
	s3_bucket=S3_BUCKET
	folders_count=0
	# Iterates through the list of items
	for item in filesToDisplay:
		#checking for sub-folders
		splittedList = list(filter(None, item.strip().split("/")))
		# if requested for subfolders then, it add all the files in the subfolder to a list
		if folderClicked is not None and folderClicked in splittedList:
			index = splittedList.index(folderClicked)
			tmp_list = []
			for i in range(index+1, len(splittedList)):
				tmp_list.append(splittedList[i])
			splittedList = tmp_list
		# for main folders
		if ("/" not in item and folderClicked.__eq__(" ")):
			insertPic(item)
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
	# Adding subfolders and current folder files to list
	folders.extend(files)
	files_folders=folders
	db = MongoDatabase.config_mongodb()
	obj = db.user.find_one({"user":user})["pics_ratings"]
	for image in obj:
		#adding the pic ratings of the image to list
		pics_with_ratings[image[0]] = image[1]
	return render_template('/gallery_index.html', **locals()) 

# Inserts the user to the db if doesn't exists
def insert_user(user):
	db = MongoDatabase.config_mongodb()
	flag = db.user.find_one({"user": user})
	if flag is None:
		user_doc = {}
		user_doc["user"] = user
		user_doc["pics_ratings"] = []
		db.user.insert(user_doc)
		print("user inserted in db")
# Inserts the user rating of the respective image files
def insert_user_rating(pic, rating):
	global USER
	if USER is not None:
		db = MongoDatabase.config_mongodb()
		obj = db.user.find_one({"user": USER})
		if obj is not None:
			picsList = obj["pics_ratings"]
			flag = False;
			#checking for the pic to rate
			for i in range(0, len(picsList)):
				if picsList[i][0].__eq__(pic):
					picsList[i][1] = rating
					flag = True
					break
			if (flag):
				# if the user updates the rating of a pic
				db.user.update({"user" : USER}, {"$set":{"pics_ratings": picsList}})
			else:
				# if the user rates the pic for first time
				db.user.update({"user" : USER}, {"$push":{"pics_ratings": [pic, rating]}})

# Inserts the pic details in db
def insertPic(fileName):
	db = MongoDatabase.config_mongodb()
	flag = db.pics.find_one({"pic_id":fileName})
	if flag is None:
		pic_doc = {}
		rating_list = []
		pic_doc["pic_id"] = fileName
		pic_doc["rating_list"] = rating_list
		db.pics.insert(pic_doc)
# Inserts the pic rating 
def pic_rating(fileName,rating):
	db = MongoDatabase.config_mongodb()
	flag = db.pics.find_one({"pic_id":fileName})
	if flag is None:
		return {"status":"failed"}
	else:
		# Adding the ratings of a pic to the resp list
		db.pics.update({"pic_id":fileName},{"$push":{"rating_list":rating}})

# when you logout from the gallery
@app.route("/logout", methods=['POST'])
def logout():
	global USER, PATH, folderClicked
	USER=""
	PATH=S3_BUCKET+"/"
	folderClicked=" "
	return redirect("/")

# this view is ratings filter
@app.route("/ratingsfilter", methods=['GET','POST'])
def ratingsfilter():
	global USER, currentFilter, filesToDisplay
	user=USER
	allFiles=[]
	db = MongoDatabase.config_mongodb()
	if request.method == 'POST':
		filterRating = request.form.get('dropdown')
		obj = db.user.find_one({"user":user})["pics_ratings"]
		# updates the filesToDisplay list with the filtered pics
		if len(filterRating) == 2:
			if filterRating[0] is '>':
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
			filesToDisplay=allFiles
		# when None filter is chosen, it displays all the pics
		if len(filterRating) > 2:
			objects = s3.list_objects(Bucket=S3_BUCKET)
			filesToDisplay= [file["Key"] for file in objects["Contents"]]
		currentFilter=filterRating
	return redirect("/gallery")

if __name__ == "__main__":
	app.run()
