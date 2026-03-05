const express = require('express');
const app = express();
app.use('/api', require('./routes/users'));
app.listen(3000);