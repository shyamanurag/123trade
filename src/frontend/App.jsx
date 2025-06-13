import {
    CssBaseline
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import React, { useEffect, useState } from 'react';

// Import components
import ComprehensiveTradingDashboard from './components/ComprehensiveTradingDashboard';
import LoginForm from './components/LoginForm';

const theme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: '#2196f3',
        },
        secondary: {
            main: '#f50057',
        },
        success: {
            main: '#4caf50',
        },
        error: {
            main: '#f44336',
        },
        warning: {
            main: '#ff9800',
        },
    },
    typography: {
        fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
        h4: {
            fontWeight: 600,
        },
        h5: {
            fontWeight: 600,
        },
        h6: {
            fontWeight: 600,
        },
    },
    components: {
        MuiCard: {
            styleOverrides: {
                root: {
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                    borderRadius: 12,
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 8,
                    textTransform: 'none',
                    fontWeight: 600,
                },
            },
        },
        MuiTab: {
            styleOverrides: {
                root: {
                    textTransform: 'none',
                    fontWeight: 600,
                },
            },
        },
    },
});

function App() {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userInfo, setUserInfo] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check for existing authentication
        const token = localStorage.getItem('access_token');
        const storedUserInfo = localStorage.getItem('user_info');

        if (token && storedUserInfo) {
            try {
                setUserInfo(JSON.parse(storedUserInfo));
                setIsAuthenticated(true);
            } catch (e) {
                console.error('Error parsing user info:', e);
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
            }
        }
        setLoading(false);
    }, []);

    const handleLogin = (loginData) => {
        setUserInfo(loginData.user_info);
        setIsAuthenticated(true);
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        setUserInfo(null);
        setIsAuthenticated(false);
    };

    if (loading) {
        return (
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <div>Loading...</div>
            </ThemeProvider>
        );
    }

    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            {isAuthenticated ? (
                <ComprehensiveTradingDashboard
                    userInfo={userInfo}
                    onLogout={handleLogout}
                />
            ) : (
                <LoginForm onLogin={handleLogin} />
            )}
        </ThemeProvider>
    );
}

export default App; 