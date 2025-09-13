import React, { useState } from 'react';
import LoginScreen from './LoginScreen';
import SignupScreen from './SignupScreen';

export default function AuthScreen() {
    const [isLogin, setIsLogin] = useState(true);

    const switchToSignup = () => setIsLogin(false);
    const switchToLogin = () => setIsLogin(true);

    if (isLogin) {
    return <LoginScreen onNavigateToSignup={switchToSignup} />;
    } else {
    return <SignupScreen onNavigateToLogin={switchToLogin} />;
    }
}