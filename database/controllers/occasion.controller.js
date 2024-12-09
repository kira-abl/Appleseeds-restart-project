const Occasion = require("../Models/Occasion.js");

class OccasionController {

	async addOccasion(req, res) {
        const { occasion, greeting, img, token } = req.body
		try {
            const newOccasion = new Occasion({occasion, greeting, img, token})
            newOccasion.save()
        
			res.send(newOccasion);
		} catch (error) {
			res.sendStatus(400);
		}
	}

    async getOccasion(req, res) {
        const occasion = req.params.occasion
        console.log(occasion)
		try {
            let returnedOccasion
            returnedOccasion = await Occasion.findOne({occasion: occasion}).exec()
			res.send(returnedOccasion);
		} catch (error) {
			res.sendStatus(400);
		}
	}
}

const occasionController = new OccasionController()
module.exports = occasionController