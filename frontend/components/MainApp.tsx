import React, { useState, useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import { User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import AuthScreen from './AuthScreen';
import HomePage from './HomePage';
import CameraScreen from './CameraScreen';
import SettingsScreen from './SettingsScreen';

type Screen = 'auth' | 'home' | 'camera' | 'settings';

export default function MainApp() {
    const [currentScreen, setCurrentScreen] = useState<Screen>('auth');
    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            setUser(session?.user ?? null);
            setCurrentScreen(session ? 'home' : 'auth');
        });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        setUser(session?.user ?? null);
        setCurrentScreen(session ? 'home' : 'auth');
    });
    return () => subscription.unsubscribe();
    }, []);

    const handleOpenCamera = () => {
        setCurrentScreen('camera');
    };

    const handleOpenSettings = () => {
        setCurrentScreen('settings');
    };

    const handleCloseCamera = () => {
        setCurrentScreen('home');
    };

    const handleCloseSettings = () => {
        setCurrentScreen('home');
    };

    const handleDataCapture = (data: any) => {
        console.log('Data captured:', data);
        setCurrentScreen('home');
    };

    const renderScreen = () => {
        switch (currentScreen) {
        case 'auth':
            return <AuthScreen />;
        case 'home':
            return <HomePage onOpenCamera={handleOpenCamera} onOpenSettings={handleOpenSettings} />;
        case 'camera':
            return (
            <CameraScreen 
                onClose={handleCloseCamera}
                onDataCapture={handleDataCapture}
            />
            );
        case 'settings':
            return <SettingsScreen onClose={handleCloseSettings} />;
        default:
            return <AuthScreen />;
        }
    };

    return (
        <View style={styles.container}>
        {renderScreen()}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
});