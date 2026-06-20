const fetchLiveScores = async () => {
  const url = "https://backend-livetips.onrender.com/livescore";

  try {
    console.log("Fetching...");

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(15000), // wait up to 15s
    });

    console.log("Status:", response.status);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    console.log("Data:", data);

  } catch (error) {
    console.error("Failed:", error.message);
  }
};

fetchLiveScores();