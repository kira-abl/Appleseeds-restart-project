import { useState } from "react";
import "./App.css";

const occasionsList = [
  "birthday",
  "wedding",
  "newborn",
  "new year",
  "graduation",
  "jewish new year",
  "muslim new year",
  "retirement",
];
function App() {
  const [selectedOccasion, setSelectedOccasion] = useState(occasionsList[0]);
  const [imageUrl, setImageUrl] = useState(null);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    try {
      const response = await fetch("https://place-holder/api/greeting", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ occasion: selectedOccasion }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch the image.");
      }

      const data = await response.json();
      setImageUrl(data.imageUrl);
      setError("");
    } catch (err) {
      setError("Failed to fetch the image. Please try again.");
      setImageUrl(null);
    }
  };

  return (
    <div className="app">
      <header>
        <nav className="header">
          <h1>Greeting Generator App</h1>
        </nav>
      </header>
      <main className="container">
        <p>Generate a greeting image based on your selected occasion.</p>
        <div className="form">
          <label htmlFor="occasion">Choose an occasion:</label>
          <select
            id="occasion"
            value={selectedOccasion}
            onChange={(e) => setSelectedOccasion(e.target.value)}
          >
            {occasionsList.map((occasion) => (
              <option key={occasion} value={occasion}>
                {occasion}
              </option>
            ))}
          </select>
          <button onClick={handleSubmit}>Generate</button>
        </div>
        {imageUrl && <img src={imageUrl} alt="Generated greeting" />}
        {error && <p className="error">{error}</p>}
      </main>
    </div>
  );
}

export default App;
