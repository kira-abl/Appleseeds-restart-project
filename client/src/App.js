import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import Spinner from "./components/spinner";
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
  const [imageUrl, setImageUrl] = useState("");
  const [greeting, setGreeting] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const token = uuidv4();
      /** Dont forget to replace fetch endoping when deploying the app to prod */
      const response = await fetch("http://localhost:5001/api/greeting", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ occasion: selectedOccasion, token }),
      });
      if (!response.ok) {
        throw new Error("Failed to fetch the image.");
      }
      const data = await response.json();
      setImageUrl(data.img);
      setGreeting(data.greeting);

      setError("");
    } catch (err) {
      setError("Failed to fetch the Greeitng. Please try again.");
      setImageUrl(null);
      setGreeting("");
    }
    setLoading(false);
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
        {loading && (
          <div>
            <Spinner />
          </div>
        )}
        <div>
          {greeting && <p className="greeting-text">{greeting}</p>}
          {imageUrl && (
            <img class="generated-image" src={imageUrl} alt="Generated img" />
          )}
          {error && <p className="error">{error}</p>}
        </div>
      </main>
    </div>
  );
}

export default App;
