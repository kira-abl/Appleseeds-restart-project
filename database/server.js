const express=require('express')
const app=express()
const mongoose = require("mongoose");
const bodyParser = require("body-parser");
const occasionController = require('./controllers/occasion.controller');
require('dotenv').config();


const port = process.env.PORT || 3001 ;
 
mongoose.connect(process.env.MONGODB_URI, {
		useNewUrlParser: true,
	})
	//  "mongodb://localhost:27017/bank"
	.then(() => console.log("conneted to DB"))
	.catch((err) => console.log(err));

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

app.post('/occasion', occasionController.addOccasion)
app.get('/occasion/:occasion', occasionController.getOccasion)

app.listen(port, function () {
	console.log("Server up and running on port ",port);
});