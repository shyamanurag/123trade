import React, { useState, useEffect } from 'react';
import {
    Box,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    IconButton,
    Typography,
    Alert,
    CircularProgress
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { useSnackbar } from 'notistack';

interface User {
    user_id: string;
    capital: number;
    risk_limits: Record<string, any>;
    trading_preferences: Record<string, any>;
    is_active: boolean;
    performance_metrics: Record<string, any>;
}

interface UserFormData {
    user_id: string;
    initial_capital: number;
    risk_limits: Record<string, any>;
    trading_preferences: Record<string, any>;
}

const UserManagement: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [openDialog, setOpenDialog] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [formData, setFormData] = useState<UserFormData>({
        user_id: '',
        initial_capital: 0,
        risk_limits: {},
        trading_preferences: {}
    });
    
    const { enqueueSnackbar } = useSnackbar();
    
    useEffect(() => {
        fetchUsers();
    }, []);
    
    const fetchUsers = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/users');
            if (!response.ok) {
                throw new Error('Failed to fetch users');
            }
            const data = await response.json();
            setUsers(data);
            setError(null);
        } catch (err) {
            setError(err.message);
            enqueueSnackbar('Error fetching users', { variant: 'error' });
        } finally {
            setLoading(false);
        }
    };
    
    const handleOpenDialog = (user?: User) => {
        if (user) {
            setEditingUser(user);
            setFormData({
                user_id: user.user_id,
                initial_capital: user.capital,
                risk_limits: user.risk_limits,
                trading_preferences: user.trading_preferences
            });
        } else {
            setEditingUser(null);
            setFormData({
                user_id: '',
                initial_capital: 0,
                risk_limits: {},
                trading_preferences: {}
            });
        }
        setOpenDialog(true);
    };
    
    const handleCloseDialog = () => {
        setOpenDialog(false);
        setEditingUser(null);
    };
    
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const url = editingUser
                ? `/api/users/${editingUser.user_id}`
                : '/api/users';
            const method = editingUser ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            if (!response.ok) {
                throw new Error('Failed to save user');
            }
            
            enqueueSnackbar(
                `User ${editingUser ? 'updated' : 'created'} successfully`,
                { variant: 'success' }
            );
            
            handleCloseDialog();
            fetchUsers();
            
        } catch (err) {
            enqueueSnackbar(err.message, { variant: 'error' });
        }
    };
    
    const handleDelete = async (userId: string) => {
        if (!window.confirm('Are you sure you want to delete this user?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/users/${userId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete user');
            }
            
            enqueueSnackbar('User deleted successfully', { variant: 'success' });
            fetchUsers();
            
        } catch (err) {
            enqueueSnackbar(err.message, { variant: 'error' });
        }
    };
    
    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <CircularProgress />
            </Box>
        );
    }
    
    if (error) {
        return (
            <Alert severity="error" sx={{ mt: 2 }}>
                {error}
            </Alert>
        );
    }
    
    return (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h5">User Management</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => handleOpenDialog()}
                >
                    Add User
                </Button>
            </Box>
            
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>User ID</TableCell>
                            <TableCell align="right">Capital</TableCell>
                            <TableCell align="right">Win Rate</TableCell>
                            <TableCell align="right">Avg Return</TableCell>
                            <TableCell align="right">Status</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {users.map((user) => (
                            <TableRow key={user.user_id}>
                                <TableCell>{user.user_id}</TableCell>
                                <TableCell align="right">
                                    ${user.capital.toLocaleString()}
                                </TableCell>
                                <TableCell align="right">
                                    {(user.performance_metrics.win_rate * 100).toFixed(1)}%
                                </TableCell>
                                <TableCell align="right">
                                    {user.performance_metrics.average_return.toFixed(2)}%
                                </TableCell>
                                <TableCell align="right">
                                    {user.is_active ? 'Active' : 'Inactive'}
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton
                                        onClick={() => handleOpenDialog(user)}
                                        color="primary"
                                    >
                                        <EditIcon />
                                    </IconButton>
                                    <IconButton
                                        onClick={() => handleDelete(user.user_id)}
                                        color="error"
                                    >
                                        <DeleteIcon />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
            
            <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {editingUser ? 'Edit User' : 'Add New User'}
                </DialogTitle>
                <form onSubmit={handleSubmit}>
                    <DialogContent>
                        <TextField
                            fullWidth
                            label="User ID"
                            value={formData.user_id}
                            onChange={(e) => setFormData({
                                ...formData,
                                user_id: e.target.value
                            })}
                            margin="normal"
                            required
                            disabled={!!editingUser}
                        />
                        <TextField
                            fullWidth
                            label="Initial Capital"
                            type="number"
                            value={formData.initial_capital}
                            onChange={(e) => setFormData({
                                ...formData,
                                initial_capital: parseFloat(e.target.value)
                            })}
                            margin="normal"
                            required
                        />
                        {/* Add more fields for risk limits and trading preferences */}
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleCloseDialog}>Cancel</Button>
                        <Button type="submit" variant="contained" color="primary">
                            {editingUser ? 'Update' : 'Create'}
                        </Button>
                    </DialogActions>
                </form>
            </Dialog>
        </Box>
    );
};

export default UserManagement; 