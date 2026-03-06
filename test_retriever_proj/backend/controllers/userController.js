const listUsers = (req, res) => { res.json([{id: 1, name: 'Alice'}]); };
module.exports = { listUsers };