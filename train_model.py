import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import pickle

print("🚀 Training model...")

# Create dataset
np.random.seed(42)
n = 500

data = pd.DataFrame({
    "experience": np.random.randint(0, 20, n),
    "age": np.random.randint(21, 65, n),
    "location": np.random.choice(["US", "Canada", "UK", "Remote"], n),
    "degree": np.random.choice(["HighSchool", "BSc", "MSc", "PhD"], n),
    "job_role": np.random.choice(["Software", "Data Analyst", "Manager"], n)
})

# Calculate salary
salary = 30000 + data["experience"] * 4000 + data["age"] * 500

# Add categorical impacts
location_impact = {"US": 20000, "Canada": 15000, "UK": 18000, "Remote": 10000}
degree_impact = {"HighSchool": 0, "BSc": 10000, "MSc": 20000, "PhD": 30000}
role_impact = {"Software": 15000, "Data Analyst": 12000, "Manager": 25000}

salary += data["location"].map(location_impact)
salary += data["degree"].map(degree_impact)
salary += data["job_role"].map(role_impact)
salary += np.random.normal(0, 5000, n)

data["salary"] = salary.astype(int)

# Prepare data
X = data.drop("salary", axis=1)
y = data["salary"]

# Create pipeline
categorical_features = ["location", "degree", "job_role"]
numeric_features = ["experience", "age"]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(drop="first", sparse_output=False), categorical_features)
    ],
    remainder="passthrough"
)

model = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", LinearRegression())
])

# Train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model.fit(X_train, y_train)

# Save
with open("salary_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model saved as 'salary_model.pkl'")
print(f"📊 Score: {model.score(X_test, y_test):.2f}")