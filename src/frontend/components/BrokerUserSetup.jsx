import { AccountCircle } from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    FormControlLabel,
    Grid,
    Step,
    StepLabel,
    Stepper,
    Switch,
    TextField,
    Typography
} from '@mui/material';
import React, { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const BrokerUserSetup = ({ open, onClose, onUserAdded }) => {
    const [activeStep, setActiveStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    const [formData, setFormData] = useState({
        user_id: '',
        name: '',
        broker: 'zerodha',
        api_key: '',
        api_secret: '',
        client_id: '',
        initial_capital: 100000,
        risk_tolerance: 'medium',
        paper_trading: true
    });

    const steps = ['User Information', 'Broker Credentials', 'Trading Settings'];

    const handleNext = () => {
        setActiveStep((prevStep) => prevStep + 1);
    };

    const handleBack = () => {
        setActiveStep((prevStep) => prevStep - 1);
    };

    const handleChange = (field) => (event) => {
        setFormData({
            ...formData,
            [field]: event.target.type === 'checkbox' ? event.target.checked : event.target.value
        });
    };

    const handleSubmit = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_BASE_URL}/api/users/broker`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok && data.success) {
                setSuccess(true);
                setTimeout(() => {
                    onUserAdded(data.user);
                    onClose();
                    // Reset form
                    setFormData({
                        user_id: '',
                        name: '',
                        broker: 'zerodha',
                        api_key: '',
                        api_secret: '',
                        client_id: '',
                        initial_capital: 100000,
                        risk_tolerance: 'medium',
                        paper_trading: true
                    });
                    setActiveStep(0);
                    setSuccess(false);
                }, 1500);
            } else {
                setError(data.detail || 'Failed to add broker user');
            }
        } catch (err) {
            setError('Network error. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getStepContent = (step) => {
        switch (step) {
            case 0:
                return (
                    <Grid container spacing={3}>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="User ID"
                                value={formData.user_id}
                                onChange={handleChange('user_id')}
                                placeholder="e.g., ZERODHA_USER_001"
                                required
                                helperText="Unique identifier for this trading account"
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Name"
                                value={formData.name}
                                onChange={handleChange('name')}
                                placeholder="e.g., John Doe"
                                required
                                helperText="Display name for the dashboard"
                            />
                        </Grid>
                    </Grid>
                );

            case 1:
                return (
                    <Grid container spacing={3}>
                        <Grid item xs={12}>
                            <Alert severity="info" sx={{ mb: 2 }}>
                                Enter your Zerodha Kite Connect API credentials. These will be used for paper trading.
                            </Alert>
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="API Key"
                                value={formData.api_key}
                                onChange={handleChange('api_key')}
                                placeholder="Your Zerodha API Key"
                                required
                                type="password"
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="API Secret"
                                value={formData.api_secret}
                                onChange={handleChange('api_secret')}
                                placeholder="Your Zerodha API Secret"
                                required
                                type="password"
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Client ID (User ID)"
                                value={formData.client_id}
                                onChange={handleChange('client_id')}
                                placeholder="Your Zerodha Client ID"
                                required
                                helperText="This is your Zerodha login ID"
                            />
                        </Grid>
                    </Grid>
                );

            case 2:
                return (
                    <Grid container spacing={3}>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                label="Initial Capital"
                                type="number"
                                value={formData.initial_capital}
                                onChange={handleChange('initial_capital')}
                                helperText="Starting capital for paper trading"
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                fullWidth
                                select
                                label="Risk Tolerance"
                                value={formData.risk_tolerance}
                                onChange={handleChange('risk_tolerance')}
                                SelectProps={{ native: true }}
                            >
                                <option value="conservative">Conservative</option>
                                <option value="medium">Medium</option>
                                <option value="aggressive">Aggressive</option>
                            </TextField>
                        </Grid>
                        <Grid item xs={12}>
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={formData.paper_trading}
                                        onChange={handleChange('paper_trading')}
                                        color="primary"
                                    />
                                }
                                label="Paper Trading Mode"
                            />
                            <Typography variant="caption" display="block" color="text.secondary">
                                Keep this enabled to trade with virtual money
                            </Typography>
                        </Grid>
                    </Grid>
                );

            default:
                return 'Unknown step';
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AccountCircle />
                    Setup Broker User
                </Box>
            </DialogTitle>

            <DialogContent>
                {error && (
                    <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                        {error}
                    </Alert>
                )}

                {success && (
                    <Alert severity="success" sx={{ mb: 2 }}>
                        Broker user added successfully! Starting trading system...
                    </Alert>
                )}

                <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
                    {steps.map((label) => (
                        <Step key={label}>
                            <StepLabel>{label}</StepLabel>
                        </Step>
                    ))}
                </Stepper>

                <Box sx={{ mt: 2 }}>
                    {getStepContent(activeStep)}
                </Box>
            </DialogContent>

            <DialogActions>
                <Button onClick={onClose} disabled={loading}>
                    Cancel
                </Button>
                <Button
                    disabled={activeStep === 0 || loading}
                    onClick={handleBack}
                >
                    Back
                </Button>
                {activeStep === steps.length - 1 ? (
                    <Button
                        variant="contained"
                        onClick={handleSubmit}
                        disabled={loading}
                    >
                        {loading ? 'Adding User...' : 'Add User & Start Trading'}
                    </Button>
                ) : (
                    <Button
                        variant="contained"
                        onClick={handleNext}
                        disabled={
                            (activeStep === 0 && (!formData.user_id || !formData.name)) ||
                            (activeStep === 1 && (!formData.api_key || !formData.api_secret || !formData.client_id))
                        }
                    >
                        Next
                    </Button>
                )}
            </DialogActions>
        </Dialog>
    );
};

export default BrokerUserSetup; 