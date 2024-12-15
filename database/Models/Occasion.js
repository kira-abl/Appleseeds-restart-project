const mongoose = require("mongoose");
const Schema = mongoose.Schema;

const occasionSchema = new Schema(
	{
		occasion: String,
		greeting: String,
		img: String,
		token: String
	},
);

const Occasion = mongoose.model("Occasion", occasionSchema);
module.exports = Occasion;