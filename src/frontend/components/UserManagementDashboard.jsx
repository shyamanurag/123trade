import {
    AccountCircle,
    Delete,
    PersonAdd,
    ShowChart,
    TrendingUp,
    Visibility,
    VisibilityOff
} from '@mui/icons-material';
import {
    Alert,
    Avatar,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    FormControl,
    Grid,
    IconButton,
    InputLabel,
    List,
    ListItem,
    ListItemAvatar,
    ListItemText,
    MenuItem,
    Paper,
    Select,
    Tab,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Tabs,
    TextField,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const UserManagementDashboard = () => {
    const [selectedTab, setSelectedTab] = useState(0);
    const [users, setUsers] = useState([]);
    const [userPositions, setUserPositions] = useState({});
    const [userTrades, setUserTrades] = useState({});
    const [userAnalytics, setUserAnalytics] = useState({});
    const [loading, setLoading] = useState(true);
    const [openDialog, setOpenDialog] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);
    const [newUserData, setNewUserData] = useState({
        username: '',
        email: '',
        password: '',
        zerodhaClientId: '',
        zerodhaPassword: '',
        initialCapital: 50000,
        riskLevel: 'medium'
    });
    const [error, setError] = useState(null);
    const [addUserLoading, setAddUserLoading] = useState(false);

    useEffect(() => {
        fetchAllData();
        // Remove the automatic refresh - data will be fetched on demand
    }, []);

    const fetchAllData = async () => {
        try {
            setLoading(true);
            // Only fetch users initially
            await fetchUsers();
            // Fetch other data only when users are selected or tabs are changed
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/api/users`);
            if (!response.ok) {
                throw new Error('Failed to fetch users');
            }
            const data = await response.json();
            if (data.success) {
                setUsers(data.users || []);
            } else {
                throw new Error(data.message || 'Failed to fetch users');
            }
        } catch (error) {
            console.error('Error fetching users:', error);
            setError('Failed to fetch users: ' + error.message);
            setUsers([]); // Set empty array instead of mock data
        } finally {
            setLoading(false);
        }
    };

    const fetchUserPositions = async (userId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/users/${userId}/positions`);
            if (!response.ok) {
                throw new Error('Failed to fetch positions');
            }
            const data = await response.json();
            if (data.success) {
                setUserPositions(prev => ({
                    ...prev,
                    [userId]: data.positions || []
                }));
            }
        } catch (error) {
            console.error('Error fetching user positions:', error);
            setUserPositions(prev => ({
                ...prev,
                [userId]: [] // Set empty array instead of mock data
            }));
        }
    };

    const fetchUserTrades = async (userId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/users/${userId}/trades?limit=10`);
            if (!response.ok) {
                throw new Error('Failed to fetch trades');
            }
            const data = await response.json();
            if (data.success) {
                setUserTrades(prev => ({
                    ...prev,
                    [userId]: data.trades || []
                }));
            }
        } catch (error) {
            console.error('Error fetching user trades:', error);
            setUserTrades(prev => ({
                ...prev,
                [userId]: [] // Set empty array instead of mock data
            }));
        }
    };

    const fetchUserAnalytics = async (userId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/users/${userId}/analytics`);
            if (!response.ok) {
                throw new Error('Failed to fetch analytics');
            }
            const data = await response.json();
            if (data.success) {
                setUserAnalytics(prev => ({
                    ...prev,
                    [userId]: data.analytics || {
                        monthly_pnl: [],
                        strategy_breakdown: [],
                        performance_metrics: {
                            total_pnl: 0,
                            win_rate: 0,
                            avg_trade_pnl: 0,
                            max_drawdown: 0,
                            sharpe_ratio: 0,
                            total_trades: 0,
                            winning_trades: 0,
                            losing_trades: 0
                        }
                    }
                }));
            }
        } catch (error) {
            console.error('Error fetching user analytics:', error);
            setUserAnalytics(prev => ({
                ...prev,
                [userId]: {
                    monthly_pnl: [],
                    strategy_breakdown: [],
                    performance_metrics: {
                        total_pnl: 0,
                        win_rate: 0,
                        avg_trade_pnl: 0,
                        max_drawdown: 0,
                        sharpe_ratio: 0,
                        total_trades: 0,
                        winning_trades: 0,
                        losing_trades: 0
                    }
                }
            }));
        }
    };

    const handleAddUser = async () => {
        try {
            setAddUserLoading(true);

            // Transform data to match backend expectations
            const userData = {
                user_id: newUserData.username,
                name: newUserData.username,
                broker: "zerodha",
                api_key: import.meta.env.VITE_ZERODHA_API_KEY,
                api_secret: import.meta.env.VITE_ZERODHA_API_SECRET,
                client_id: newUserData.zerodhaClientId,
                initial_capital: newUserData.initialCapital,
                risk_tolerance: newUserData.riskLevel,
                paper_trading: true
            };

            const response = await fetch(`${API_BASE_URL}/api/users/broker`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to add user');
            }

            const data = await response.json();
            if (data.success) {
                await fetchUsers(); // Refresh users list
                setNewUserData({
                    username: '',
                    email: '',
                    password: '',
                    zerodhaClientId: '',
                    zerodhaPassword: '',
                    initialCapital: 50000,
                    riskLevel: 'medium'
                });
                setOpenDialog(false);
                setError(null);
            } else {
                throw new Error(data.message || 'Failed to add user');
            }
        } catch (error) {
            console.error('Error adding user:', error);
            setError('Failed to add user: ' + error.message);
        } finally {
            setAddUserLoading(false);
        }
    };

    const handleRemoveUser = async (userId) => {
        if (!window.confirm('Are you sure you want to remove this user? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to remove user');
            }

            const data = await response.json();
            if (data.success) {
                await fetchUsers(); // Refresh users list
                setError(null);
            } else {
                throw new Error(data.message || 'Failed to remove user');
            }
        } catch (error) {
            console.error('Error removing user:', error);
            setError('Failed to remove user: ' + error.message);
        }
    };

    const handleToggleUserStatus = async (userId) => {
        try {
            setUsers(prev => prev.map(user =>
                user.id === userId
                    ? { ...user, status: user.status === 'active' ? 'inactive' : 'active' }
                    : user
            ));
        } catch (error) {
            console.error('Error updating user status:', error);
        }
    };

    const formatCurrency = (value) => `₹${value?.toLocaleString() || 0}`;
    const formatPercent = (value) => `${value?.toFixed(1) || 0}%`;

    const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

    const TabPanel = ({ children, value, index }) => (
        <div hidden={value !== index}>
            {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
        </div>
    );

    // Fetch positions and trades only when switching to those tabs
    useEffect(() => {
        if (selectedTab === 1 && users.length > 0) {
            // Real-time Positions tab - fetch positions for active users
            users.filter(user => user.status === 'active').forEach(user => {
                fetchUserPositions(user.id);
            });
        } else if (selectedTab === 2 && users.length > 0) {
            // User Analytics tab - fetch analytics for all users
            users.forEach(user => {
                fetchUserAnalytics(user.id);
            });
        }
    }, [selectedTab, users]);

    return (
        <Box>
            <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
                👥 User Management & Analytics
            </Typography>

            {/* Error Display */}
            {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Navigation Tabs */}
            <Paper sx={{ mb: 3 }}>
                <Tabs
                    value={selectedTab}
                    onChange={(e, newValue) => setSelectedTab(newValue)}
                    variant="scrollable"
                    scrollButtons="auto"
                >
                    <Tab icon={<AccountCircle />} label="User Overview" />
                    <Tab icon={<TrendingUp />} label="Real-time Positions" />
                    <Tab icon={<ShowChart />} label="User Analytics" />
                    <Tab icon={<PersonAdd />} label="User Management" />
                </Tabs>
            </Paper>

            {/* Tab Panels */}
            <TabPanel value={selectedTab} index={0}>
                {/* User Overview */}
                <Grid container spacing={3}>
                    {users.map((user) => (
                        <Grid item xs={12} md={6} lg={4} key={user.id}>
                            <Card>
                                <CardContent>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                        <Box>
                                            <Typography variant="h6">{user.username}</Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                {user.zerodhaClientId}
                                            </Typography>
                                        </Box>
                                        <Chip
                                            label={user.status}
                                            color={user.status === 'active' ? 'success' : 'default'}
                                            size="small"
                                        />
                                    </Box>

                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="body2">Current Balance:</Typography>
                                        <Typography variant="body2" fontWeight="bold">
                                            {formatCurrency(user.currentBalance)}
                                        </Typography>
                                    </Box>

                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="body2">Total P&L:</Typography>
                                        <Typography
                                            variant="body2"
                                            fontWeight="bold"
                                            color={user.totalPnL >= 0 ? 'success.main' : 'error.main'}
                                        >
                                            {formatCurrency(user.totalPnL)}
                                        </Typography>
                                    </Box>

                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="body2">Win Rate:</Typography>
                                        <Typography variant="body2" fontWeight="bold">
                                            {formatPercent(user.winRate)}
                                        </Typography>
                                    </Box>

                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                                        <Typography variant="body2">Total Trades:</Typography>
                                        <Typography variant="body2" fontWeight="bold">
                                            {user.totalTrades}
                                        </Typography>
                                    </Box>

                                    <Box sx={{ display: 'flex', gap: 1 }}>
                                        <Button
                                            size="small"
                                            onClick={() => setSelectedUser(user)}
                                            variant="outlined"
                                        >
                                            View Details
                                        </Button>
                                        <IconButton
                                            size="small"
                                            onClick={() => handleToggleUserStatus(user.id)}
                                            color={user.status === 'active' ? 'error' : 'success'}
                                        >
                                            {user.status === 'active' ? <VisibilityOff /> : <Visibility />}
                                        </IconButton>
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            </TabPanel>

            <TabPanel value={selectedTab} index={1}>
                {/* Real-time Positions */}
                <Grid container spacing={3}>
                    {users.filter(user => user.status === 'active').map((user) => (
                        <Grid item xs={12} key={user.id}>
                            <Card>
                                <CardContent>
                                    <Typography variant="h6" sx={{ mb: 2 }}>
                                        {user.username} - Current Positions
                                    </Typography>

                                    {userPositions[user.id] && userPositions[user.id].length > 0 ? (
                                        <TableContainer>
                                            <Table size="small">
                                                <TableHead>
                                                    <TableRow>
                                                        <TableCell>Symbol</TableCell>
                                                        <TableCell align="right">Quantity</TableCell>
                                                        <TableCell align="right">Entry Price</TableCell>
                                                        <TableCell align="right">Current Price</TableCell>
                                                        <TableCell align="right">Unrealized P&L</TableCell>
                                                        <TableCell>Strategy</TableCell>
                                                    </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                    {userPositions[user.id].map((position, index) => (
                                                        <TableRow key={index}>
                                                            <TableCell>{position.symbol}</TableCell>
                                                            <TableCell align="right">{position.quantity}</TableCell>
                                                            <TableCell align="right">{formatCurrency(position.entryPrice)}</TableCell>
                                                            <TableCell align="right">{formatCurrency(position.currentPrice)}</TableCell>
                                                            <TableCell
                                                                align="right"
                                                                sx={{
                                                                    color: position.unrealizedPnL >= 0 ? 'success.main' : 'error.main',
                                                                    fontWeight: 'bold'
                                                                }}
                                                            >
                                                                {formatCurrency(position.unrealizedPnL)}
                                                            </TableCell>
                                                            <TableCell>{position.strategy}</TableCell>
                                                        </TableRow>
                                                    ))}
                                                </TableBody>
                                            </Table>
                                        </TableContainer>
                                    ) : (
                                        <Typography variant="body2" color="text.secondary">
                                            No open positions
                                        </Typography>
                                    )}
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            </TabPanel>

            <TabPanel value={selectedTab} index={2}>
                {/* User Analytics */}
                <Grid container spacing={3}>
                    {users.map((user) => (
                        <Grid item xs={12} lg={6} key={user.id}>
                            <Card>
                                <CardContent>
                                    <Typography variant="h6" sx={{ mb: 2 }}>
                                        {user.username} - Performance Analytics
                                    </Typography>

                                    {/* Monthly P&L Chart */}
                                    <Box sx={{ mb: 3 }}>
                                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Monthly P&L Trend</Typography>
                                        <ResponsiveContainer width="100%" height={200}>
                                            <AreaChart data={userAnalytics[user.id]?.monthly_pnl || []}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="month" />
                                                <YAxis />
                                                <Tooltip formatter={(value) => [formatCurrency(value), 'P&L']} />
                                                <Area
                                                    type="monotone"
                                                    dataKey="pnl"
                                                    stroke="#2196f3"
                                                    fill="#2196f3"
                                                    fillOpacity={0.3}
                                                />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </Box>

                                    {/* Strategy Breakdown */}
                                    <Box>
                                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Strategy Performance</Typography>
                                        <List dense>
                                            {userAnalytics[user.id]?.strategy_breakdown?.map((strategy, index) => (
                                                <ListItem key={index}>
                                                    <ListItemAvatar>
                                                        <Avatar sx={{ bgcolor: COLORS[index % COLORS.length], width: 24, height: 24 }}>
                                                            {strategy.value}%
                                                        </Avatar>
                                                    </ListItemAvatar>
                                                    <ListItemText
                                                        primary={strategy.name}
                                                        secondary={
                                                            <Typography
                                                                variant="body2"
                                                                color={strategy.pnl >= 0 ? 'success.main' : 'error.main'}
                                                            >
                                                                {formatCurrency(strategy.pnl)}
                                                            </Typography>
                                                        }
                                                    />
                                                </ListItem>
                                            )) || []}
                                        </List>
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            </TabPanel>

            <TabPanel value={selectedTab} index={3}>
                {/* User Management */}
                <Grid container spacing={3}>
                    <Grid item xs={12}>
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                                    <Typography variant="h6">User Management</Typography>
                                    <Button
                                        variant="contained"
                                        startIcon={<PersonAdd />}
                                        onClick={() => setOpenDialog(true)}
                                    >
                                        Add New User
                                    </Button>
                                </Box>

                                <TableContainer>
                                    <Table>
                                        <TableHead>
                                            <TableRow>
                                                <TableCell>Username</TableCell>
                                                <TableCell>Email</TableCell>
                                                <TableCell>Zerodha Client ID</TableCell>
                                                <TableCell align="right">Capital</TableCell>
                                                <TableCell align="right">Current P&L</TableCell>
                                                <TableCell>Status</TableCell>
                                                <TableCell>Join Date</TableCell>
                                                <TableCell align="center">Actions</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {users.map((user) => (
                                                <TableRow key={user.id}>
                                                    <TableCell>{user.username}</TableCell>
                                                    <TableCell>{user.email}</TableCell>
                                                    <TableCell>{user.zerodhaClientId}</TableCell>
                                                    <TableCell align="right">{formatCurrency(user.capital)}</TableCell>
                                                    <TableCell
                                                        align="right"
                                                        sx={{ color: user.totalPnL >= 0 ? 'success.main' : 'error.main' }}
                                                    >
                                                        {formatCurrency(user.totalPnL)}
                                                    </TableCell>
                                                    <TableCell>
                                                        <Chip
                                                            label={user.status}
                                                            color={user.status === 'active' ? 'success' : 'default'}
                                                            size="small"
                                                        />
                                                    </TableCell>
                                                    <TableCell>{user.joinDate}</TableCell>
                                                    <TableCell align="center">
                                                        <IconButton
                                                            size="small"
                                                            onClick={() => handleToggleUserStatus(user.id)}
                                                            color={user.status === 'active' ? 'warning' : 'success'}
                                                        >
                                                            {user.status === 'active' ? <VisibilityOff /> : <Visibility />}
                                                        </IconButton>
                                                        <IconButton
                                                            size="small"
                                                            color="error"
                                                            onClick={() => handleRemoveUser(user.id)}
                                                        >
                                                            <Delete />
                                                        </IconButton>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            </TabPanel>

            {/* Add User Dialog */}
            <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
                <form onSubmit={(e) => {
                    e.preventDefault();
                    handleAddUser();
                }}>
                    <DialogTitle>Add New User</DialogTitle>
                    <DialogContent>
                        <TextField
                            fullWidth
                            label="Username"
                            value={newUserData.username}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, username: e.target.value }))}
                            margin="normal"
                            required
                        />
                        <TextField
                            fullWidth
                            label="Email"
                            type="email"
                            value={newUserData.email}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, email: e.target.value }))}
                            margin="normal"
                            required
                        />
                        <TextField
                            fullWidth
                            label="Password"
                            type="password"
                            value={newUserData.password}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, password: e.target.value }))}
                            margin="normal"
                            required
                        />
                        <TextField
                            fullWidth
                            label="Zerodha Client ID"
                            value={newUserData.zerodhaClientId}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, zerodhaClientId: e.target.value }))}
                            margin="normal"
                            required
                        />
                        <TextField
                            fullWidth
                            label="Zerodha Password"
                            type="password"
                            value={newUserData.zerodhaPassword}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, zerodhaPassword: e.target.value }))}
                            margin="normal"
                            required
                            helperText="Required for authentication with our master API key"
                        />
                        <TextField
                            fullWidth
                            label="Initial Capital"
                            type="number"
                            value={newUserData.initialCapital}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, initialCapital: parseInt(e.target.value) }))}
                            margin="normal"
                            required
                        />
                        <FormControl fullWidth margin="normal">
                            <InputLabel>Risk Level</InputLabel>
                            <Select
                                value={newUserData.riskLevel}
                                onChange={(e) => setNewUserData(prev => ({ ...prev, riskLevel: e.target.value }))}
                            >
                                <MenuItem value="low">Low Risk</MenuItem>
                                <MenuItem value="medium">Medium Risk</MenuItem>
                                <MenuItem value="high">High Risk</MenuItem>
                            </Select>
                        </FormControl>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
                        <Button
                            type="submit"
                            variant="contained"
                            disabled={!newUserData.username || !newUserData.email || !newUserData.zerodhaClientId || addUserLoading}
                        >
                            {addUserLoading ? 'Adding...' : 'Add User'}
                        </Button>
                    </DialogActions>
                </form>
            </Dialog>
        </Box>
    );
};

export default UserManagementDashboard; 