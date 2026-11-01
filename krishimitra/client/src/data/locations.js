// Curated list. Coordinates are APPROXIMATE district centres, shown to the user and editable.
// Choose "Other" to enter any state/district/coordinates manually. Nothing is guessed silently.
const L = (state, district, latitude, longitude) => ({ state, district, latitude, longitude });
export const LOCATIONS = [
  L("Andhra Pradesh", "Anantapur", 14.68, 77.6), L("Andhra Pradesh", "Kurnool", 15.83, 78.04),
  L("Andhra Pradesh", "Guntur", 16.31, 80.44), L("Andhra Pradesh", "Krishna", 16.19, 81.14),
  L("Telangana", "Warangal", 17.97, 79.59), L("Telangana", "Karimnagar", 18.44, 79.13),
  L("Karnataka", "Raichur", 16.21, 77.36), L("Maharashtra", "Pune", 18.52, 73.86),
  L("Maharashtra", "Nagpur", 21.15, 79.09), L("Gujarat", "Rajkot", 22.3, 70.8),
  L("Punjab", "Ludhiana", 30.9, 75.86), L("Tamil Nadu", "Coimbatore", 11.02, 76.96),
  L("Uttar Pradesh", "Lucknow", 26.85, 80.95), L("West Bengal", "Hooghly", 22.9, 88.39),
  L("Kerala", "Thrissur", 10.53, 76.21),
];
export const STATES = [...new Set(LOCATIONS.map((l) => l.state))];
export const GROWTH_STAGES = ["unknown", "land_preparation", "sowing", "seedling", "vegetative", "flowering", "fruiting", "harvesting"];
export const LANGUAGES = [["en", "English"], ["te", "తెలుగు"], ["hi", "हिन्दी"], ["kn", "ಕನ್ನಡ"], ["ta", "தமிழ்"], ["ml", "മലയാളം"], ["mr", "मराठी"], ["bn", "বাংলা"], ["gu", "ગુજરાતી"]];
export const EXAMPLE_QUESTIONS = [
  "There may be rain tomorrow. Should I irrigate my field today?",
  "Which market has the best price for my crop?",
  "What does my soil pH mean?",
  "What exact pesticide dose should I spray?",
];
