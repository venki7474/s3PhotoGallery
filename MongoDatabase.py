from pymongo import MongoClient
def config_mongodb():
	client = MongoClient('localhost',27017)
	db = client.photogallery
	return db