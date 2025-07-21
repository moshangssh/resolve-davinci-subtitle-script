import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [apiResponse, setApiResponse] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchApiData = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/test");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setApiResponse(data.message);
      } catch (e: any) {
        console.error("Error fetching API:", e);
        setError(`Failed to fetch from backend: ${e.message}`);
      }
    };

    fetchApiData();
  }, []);

  return (
    <main className="container">
      <h1>Subvigator Next</h1>
      <h2>(FastAPI + React + Tauri)</h2>
      <div className="status-box">
        <h3>Backend Connection Status</h3>
        {error ? (
          <p className="status-error">
            <strong>Error:</strong> {error}
          </p>
        ) : (
          <p className="status-success">
            <strong>API Response:</strong> {apiResponse || "Loading..."}
          </p>
        )}
      </div>
    </main>
  );
}

export default App;
