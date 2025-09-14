import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, TextInput, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface SettingsScreenProps {
    onClose?: () => void;
}

export default function SettingsScreen({ onClose }: SettingsScreenProps) {
    const [homeAddress, setHomeAddress] = useState<string>('');
    const [homeCoordinates, setHomeCoordinates] = useState<{latitude: number, longitude: number} | null>(null);
    const [isSettingHome, setIsSettingHome] = useState(false);

    useEffect(() => {
        loadHomeLocation();
    }, []);

    const loadHomeLocation = async () => {
        try {
            const savedHome = await AsyncStorage.getItem('homeLocation');
            if (savedHome) {
                const homeData = JSON.parse(savedHome);
                setHomeAddress(homeData.address || '');
                setHomeCoordinates(homeData.coordinates || null);
            }
        } catch (error) {
            console.error('Error loading home location:', error);
        }
    };

  const saveHomeLocation = async (address: string, coordinates: {latitude: number, longitude: number}) => {
    try {
        const homeData = {
            address,
            coordinates,
            timestamp: new Date().toISOString()
        };
        await AsyncStorage.setItem('homeLocation', JSON.stringify(homeData));
        setHomeAddress(address);
        setHomeCoordinates(coordinates);
        Alert.alert('Success', 'Home location saved successfully!');
    } catch (error) {
        Alert.alert('Error', 'Failed to save home location.');
    }
};

const setCurrentLocationAsHome = async () => {
    setIsSettingHome(true);
    try {
        let { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
            Alert.alert('Permission Required', 'Location permission is needed to set current location as home.');
            setIsSettingHome(false);
            return;
        }

        let currentLocation = await Location.getCurrentPositionAsync({});
      
        let reverseGeocode = await Location.reverseGeocodeAsync({
            latitude: currentLocation.coords.latitude,
            longitude: currentLocation.coords.longitude,
        });

        let address = 'Current Location';
        if (reverseGeocode.length > 0) {
            const addr = reverseGeocode[0];
            address = `${addr.street || ''} ${addr.city || ''}, ${addr.region || ''}`.trim() || 'Current Location';
        }

        await saveHomeLocation(address, {
            latitude: currentLocation.coords.latitude,
            longitude: currentLocation.coords.longitude
        });
    } catch (error) {
        Alert.alert('Error', 'Failed to get current location.');
    }
    setIsSettingHome(false);
};

const searchLocationAsHome = async () => {
    if (!homeAddress.trim()) {
        Alert.alert('Error', 'Please enter an address to search.');
        return;
    }

    try {
        setIsSettingHome(true);
        
        console.log('Geocoding address:', homeAddress); 
        
        let searchAddress = homeAddress;
        // if (!homeAddress.toLowerCase().includes('cambridge') && !homeAddress.toLowerCase().includes('ma')) {
        //     searchAddress = `${homeAddress}, Cambridge, MA, USA`;
        //     console.log('Enhanced address for geocoding:', searchAddress); 
        // }
        
        let geocode = await Location.geocodeAsync(searchAddress);
        
        
        if (geocode.length === 0) {
            Alert.alert('Error', 'Address not found. Please try a different address.');
            setIsSettingHome(false);
            return;
        }

        if (geocode.length > 1) {
            geocode.forEach((result, index) => {
                console.log(`Result ${index}:`, result.latitude, result.longitude); 
            });
        }

        const coordinates = {
            latitude: geocode[0].latitude,
            longitude: geocode[0].longitude
        };

        console.log('Selected coordinates from geocoding:', coordinates);

        try {
            let reverseGeocode = await Location.reverseGeocodeAsync({
                latitude: coordinates.latitude,
                longitude: coordinates.longitude,
            });
            
            if (reverseGeocode.length > 0) {
                const addr = reverseGeocode[0];
                const verificationAddress = `${addr.street || ''} ${addr.city || ''}, ${addr.region || ''}`.trim();
                
                Alert.alert(
                    'Confirm Location',
                    `Searched: "${homeAddress}"\nFound: "${verificationAddress}"\nCoordinates: ${coordinates.latitude.toFixed(6)}, ${coordinates.longitude.toFixed(6)}\n\nIs this correct?`,
                    [
                        { text: 'No, try different address', style: 'cancel' },
                        { 
                            text: 'Yes, save it', 
                            onPress: async () => {
                                await saveHomeLocation(homeAddress, coordinates);
                            }
                        }
                    ]
                );
            } else {
                // Fallback if reverse geocoding fails
                await saveHomeLocation(homeAddress, coordinates);
            }
        } catch (reverseError) {
            await saveHomeLocation(homeAddress, coordinates);
        }

    } catch (error) {
        Alert.alert('Error', 'Failed to find address. Please check the address and try again.');
    }
    setIsSettingHome(false);
};

const clearHomeLocation = async () => {
    Alert.alert(
        'Clear Home Location',
        'Are you sure you want to remove the saved home location?',
        [
        { text: 'Cancel', style: 'cancel' },
        { 
            text: 'Clear', 
            style: 'destructive',
            onPress: async () => {
                try {
                    await AsyncStorage.removeItem('homeLocation');
                    setHomeAddress('');
                    setHomeCoordinates(null);
                    Alert.alert('Success', 'Home location cleared.');
                } catch (error) {
                    Alert.alert('Error', 'Failed to clear home location.');
                }
            }
        }
        ]
    );
};

return (
    <LinearGradient
        colors={['#1a0033', '#4a0080', '#8a2be2', '#9932cc']}
        style={styles.container}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 1 }}
    >
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
            <View style={styles.header}>
                <Text style={styles.title}>Settings</Text>
                <TouchableOpacity style={styles.closeButton} onPress={onClose}>
                    <Ionicons name="close" size={24} color="white" />
                </TouchableOpacity>
            </View>

            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Home Location</Text>
                <Text style={styles.sectionDescription}>
                    Set your home address for quick navigation and safety features.
                </Text>

                {homeCoordinates && (
                <View style={styles.currentHomeContainer}>
                    <Ionicons name="home" size={20} color="white" />
                    <View style={styles.currentHomeText}>
                        <Text style={styles.currentHomeLabel}>Current Home:</Text>
                        <Text style={styles.currentHomeAddress}>{homeAddress}</Text>
                    </View>
                </View>
                )}

                <View style={styles.inputContainer}>
                    <Text style={styles.inputLabel}>Enter Home Address:</Text>
                    <TextInput
                    style={styles.addressInput}
                    value={homeAddress}
                    onChangeText={setHomeAddress}
                    placeholder="123 Main St, City, State"
                    placeholderTextColor="rgba(255,255,255,0.5)"
                    multiline
                    />
                </View>

                <View style={styles.buttonContainer}>
                    <TouchableOpacity 
                    style={styles.actionButton}
                    onPress={searchLocationAsHome}
                    disabled={isSettingHome}
                    >
                        <Ionicons name="search" size={20} color="white" />
                        <Text style={styles.buttonText}>
                            {isSettingHome ? 'Searching...' : 'Search & Save Address'}
                        </Text>
                    </TouchableOpacity>

                    <TouchableOpacity 
                    style={styles.actionButton}
                    onPress={setCurrentLocationAsHome}
                    disabled={isSettingHome}
                    >
                        <Ionicons name="location" size={20} color="white" />
                        <Text style={styles.buttonText}>
                            {isSettingHome ? 'Getting Location...' : 'Use Current Location'}
                        </Text>
                    </TouchableOpacity>

                    {homeCoordinates && (
                        <TouchableOpacity 
                            style={[styles.actionButton, styles.clearButton]}
                            onPress={clearHomeLocation}
                        >
                            <Ionicons name="trash" size={20} color="white" />
                            <Text style={styles.buttonText}>Clear Home Location</Text>
                        </TouchableOpacity>
                    )}
                </View>
            </View>
        </ScrollView>
    </LinearGradient>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    scrollView: {
        flex: 1,
    },
    content: {
        padding: 20,
        paddingTop: 60,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 30,
    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        color: 'white',
    },
    closeButton: {
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderRadius: 20,
        padding: 8,
    },
    section: {
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        borderRadius: 15,
        padding: 20,
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.2)',
    },
    sectionTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 8,
    },
    sectionDescription: {
        fontSize: 14,
        color: 'rgba(255, 255, 255, 0.8)',
        marginBottom: 20,
        lineHeight: 20,
    },
    currentHomeContainer: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        padding: 15,
        borderRadius: 10,
        marginBottom: 20,
    },
    currentHomeText: {
        marginLeft: 12,
        flex: 1,
    },
    currentHomeLabel: {
        fontSize: 12,
        color: 'rgba(255, 255, 255, 0.7)',
        marginBottom: 4,
    },
    currentHomeAddress: {
        fontSize: 14,
        color: 'white',
        fontWeight: '500',
    },
    inputContainer: {
        marginBottom: 20,
    },
    inputLabel: {
        fontSize: 14,
        color: 'white',
        marginBottom: 8,
        fontWeight: '500',
    },
    addressInput: {
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        borderRadius: 10,
        padding: 15,
        color: 'white',
        fontSize: 16,
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.2)',
        minHeight: 50,
        textAlignVertical: 'top',
    },
    buttonContainer: {
        gap: 12,
    },
    actionButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderRadius: 12,
        padding: 15,
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.3)',
    },
    clearButton: {
        backgroundColor: 'rgba(255, 100, 100, 0.3)',
        borderColor: 'rgba(255, 100, 100, 0.5)',
    },
    buttonText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
        marginLeft: 8,
    },
});