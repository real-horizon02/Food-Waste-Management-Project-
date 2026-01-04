// server.js - simple express example (NOT production-grade)
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('../')); // serve the front-end files (index.html etc) if you run from server folder

const PORT = process.env.PORT || 3000;

// In-memory user store (demo)
const users = {}; // email -> {id,name,email,password,household}

// Helper: simple token generator (for demo only)
function createToken(user) {
  return Buffer.from(`${user.id}:${user.email}:${Date.now()}`).toString('base64');
}

// Register endpoint
app.post('/api/register', (req, res) => {
  const { name, email, password, household } = req.body || {};
  if(!name || !email || !password) return res.status(400).json({message:'Missing required fields'});
  if(users[email]) return res.status(400).json({message:'User already exists'});
  const id = uuidv4();
  users[email] = { id, name, email, password, household: household || 1 };
  const token = createToken(users[email]);
  res.json({ message: 'Registered', token });
});

// Login endpoint
app.post('/api/login', (req, res) => {
  const { identifier, password } = req.body || {};
  if(!identifier || !password) return res.status(400).json({message:'Missing credentials'});
  // try find by email or username (we use email)
  const user = users[identifier] || Object.values(users).find(u => u.email === identifier);
  if(!user) return res.status(401).json({message:'Invalid credentials'});
  if(user.password !== password) return res.status(401).json({message:'Invalid credentials'});
  const token = createToken(user);
  res.json({ message: 'Authenticated', token });
});

// Simple protected test route
app.get('/api/profile', (req, res) => {
  // token-based auth demo; not secure
  const auth = req.headers['authorization'] || '';
  if(!auth) return res.status(401).json({message:'Unauthorized'});
  // parse token and respond demo
  res.json({ message: 'This is a demo protected profile endpoint.'});
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
