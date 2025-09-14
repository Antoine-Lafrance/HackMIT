import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, Dimensions, Linking } from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import * as ScreenOrientation from 'expo-screen-orientation';
import * as Location from 'expo-location';
import * as Contacts from 'expo-contacts';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface CameraScreenProps {
    onClose?: () => void;
    onDataCapture?: (data: any) => void;
}

export default function CameraScreen({ onClose, onDataCapture }: CameraScreenProps) {
    const [facing, setFacing] = useState<CameraType>('back');
    const [permission, requestPermission] = useCameraPermissions();
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
    const [location, setLocation] = useState<Location.LocationObject | null>(null);
    const [address, setAddress] = useState<string>('Loading location...');
    const [homeLocation, setHomeLocation] = useState<{latitude: number, longitude: number} | null>(null);
    const [hasCheckedIfLost, setHasCheckedIfLost] = useState(false);
    const cameraRef = useRef<CameraView>(null);

    const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = 
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
            Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    };

    const loadHomeLocation = async () => {
        try {
            const savedHome = await AsyncStorage.getItem('homeLocation');
            if (savedHome) {
                const homeData = JSON.parse(savedHome);
                setHomeLocation(homeData.coordinates || null);
            } else {
                console.log('No home location saved');
            }
        } catch (error) {
            console.error('Error loading home location:', error);
        }
    };

    const getHomeLocationFromStorage = async () => {
        try {
            const savedHome = await AsyncStorage.getItem('homeLocation');
            if (savedHome) {
                const homeData = JSON.parse(savedHome);
                return homeData.coordinates || null;
            }
            return null;
        } catch (error) {
            console.error('Error loading home location:', error);
            return null;
        }
    };

    const checkIfLost = async (currentLat: number, currentLon: number) => {
        if (hasCheckedIfLost) {
            return;
        }

        const loadedHomeLocation = await getHomeLocationFromStorage();
        
        if (!loadedHomeLocation) {
            return;
        }

        const distanceFromHome = calculateDistance(
            currentLat, 
            currentLon, 
            loadedHomeLocation.latitude, 
            loadedHomeLocation.longitude
        );

        const DISTANCE_THRESHOLD = 1; 
        
        if (distanceFromHome > DISTANCE_THRESHOLD) {
            setHasCheckedIfLost(true); // Only ask once per session
            
            Alert.alert(
                'Are you lost?',
                `You are ${distanceFromHome.toFixed(1)}km from your home location. Do you need help getting back?`,
                [
                    { 
                        text: 'I\'m OK', 
                        style: 'cancel',
                        onPress: () => console.log('User selected: I\'m OK')
                    },
                    { 
                        text: 'Call Caretaker', 
                        onPress: async () => {
                            console.log('User selected: Call Caretaker');
                            try {
                                const { status } = await Contacts.requestPermissionsAsync();
                                if (status === 'granted') {
                                    const { data } = await Contacts.getContactsAsync({
                                        fields: [Contacts.Fields.Name, Contacts.Fields.PhoneNumbers],
                                        name: 'Caretaker'
                                    });
                                    
                                    if (data.length > 0 && data[0].phoneNumbers && data[0].phoneNumbers.length > 0) {
                                        const phoneNumber = data[0].phoneNumbers[0].number;
                                        const phoneUrl = `tel:${phoneNumber}`;
                                        Linking.openURL(phoneUrl);
                                    } else {
                                        Alert.alert('Error', 'Caretaker contact not found or has no phone number.');
                                    }
                                } else {
                                    Alert.alert('Error', 'Cannot access contacts to call caretaker.');
                                }
                            } catch (error) {
                                Alert.alert('Error', 'Failed to call caretaker.');
                            }
                        }
                    },
                    { 
                        text: 'Get Directions Home', 
                        onPress: () => {
                            // Open maps with directions to home
                            const mapsUrl = `maps://app?daddr=${loadedHomeLocation.latitude},${loadedHomeLocation.longitude}`;
                            const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${loadedHomeLocation.latitude},${loadedHomeLocation.longitude}`;
                            
                            Linking.canOpenURL(mapsUrl).then(supported => {
                                if (supported) {
                                    Linking.openURL(mapsUrl);
                                } else {
                                    Linking.openURL(googleMapsUrl);
                                }
                            });
                        }
                    }
                ]
            );
        } else {
            console.log('Not showing alert - Distance:', distanceFromHome, 'km (under threshold)');
        }
    };

    useEffect(() => {
    const lockOrientation = async () => {
        await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE);
    };
    lockOrientation();

    setIsAnalyzing(true);
    loadHomeLocation();

    const timeInterval = setInterval(() => {
        setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);

    const getLocation = async () => {
        try {
            let { status } = await Location.requestForegroundPermissionsAsync();
            if (status !== 'granted') {
                setAddress('Location permission denied');
                return;
            }

            let currentLocation = await Location.getCurrentPositionAsync({});
            setLocation(currentLocation);
            setTimeout(() => {
                checkIfLost(currentLocation.coords.latitude, currentLocation.coords.longitude);
            }, 2000);

            let reverseGeocode = await Location.reverseGeocodeAsync({
                latitude: currentLocation.coords.latitude,
                longitude: currentLocation.coords.longitude,
            });

            if (reverseGeocode.length > 0) {
                const addr = reverseGeocode[0];
                const formattedAddress = `${addr.street || ''} ${addr.city || ''}, ${addr.region || ''}`.trim();
                setAddress(formattedAddress || 'Address unavailable');
            } else {
                setAddress(`${currentLocation.coords.latitude.toFixed(4)}, ${currentLocation.coords.longitude.toFixed(4)}`);
            }
        } catch (error) {
            console.error('Error getting location:', error);
            setAddress('Location unavailable');
        }
    };

    getLocation();

    return () => {
        ScreenOrientation.unlockAsync();
        setIsAnalyzing(false);
        clearInterval(timeInterval);
    };
    }, []);

    if (!permission) {
        return <View style={styles.container} />;
    }

    if (!permission.granted) {
    return (
        <View style={styles.container}>
        <View style={styles.permissionContainer}>
            <Text style={styles.message}>Camera access required for smart glasses mode</Text>
            <TouchableOpacity style={styles.button} onPress={requestPermission}>
            <Text style={styles.buttonText}>Grant Permission</Text>
            </TouchableOpacity>
        </View>
        </View>
    );
    }

    const handleExit = async () => {
        if (onClose) {
            await ScreenOrientation.unlockAsync();
            onClose();
        }
    };

    return (
        <View style={styles.container}>
            <CameraView 
                style={styles.camera} 
                facing={facing}
                ref={cameraRef}
            >
            <View style={styles.topOverlay}>
                <View style={styles.statusContainer}>
                <View style={styles.statusItem}>
                    <View style={[styles.statusDot, { backgroundColor: isAnalyzing ? '#00ff00' : '#ff0000' }]} />
                    <Text style={styles.statusText}>
                    {isAnalyzing ? 'ANALYZING' : 'STANDBY'}
                    </Text>
                </View>
                <Text style={styles.timeText}>
                    {currentTime}
                </Text>
                <View style={styles.locationItem}>
                    <Ionicons name="location-outline" size={12} color="white" />
                    <Text style={styles.locationText}>
                    {address}
                    </Text>
                </View>
                </View>
                
                <TouchableOpacity style={styles.exitButton} onPress={handleExit}>
                <Ionicons name="close" size={24} color="white" />
                </TouchableOpacity>
            </View>

            <View style={styles.bottomOverlay}>
                <View style={styles.glassesInfo}>
                <Text style={styles.glassesText}>Smart Glasses Mode</Text>
                <Text style={styles.glassesSubtext}>Here are your surroundings</Text>
                </View>
            </View>

            <View style={styles.crosshair}>
                <View style={styles.crosshairHorizontal} />
                <View style={styles.crosshairVertical} />
            </View>
            </CameraView>
        </View>
    );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  permissionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  message: {
    textAlign: 'center',
    paddingBottom: 20,
    color: 'white',
    fontSize: 16,
  },
  camera: {
    flex: 1,
  },
  topOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 20,
    paddingTop: 40,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  statusContainer: {
    flexDirection: 'column',
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  timeText: {
    color: 'white',
    fontSize: 12,
    opacity: 0.8,
  },
  locationItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 5,
  },
  locationText: {
    color: 'white',
    fontSize: 11,
    opacity: 0.8,
    marginLeft: 4,
    maxWidth: 200,
  },
  exitButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    borderRadius: 20,
    padding: 8,
  },
  bottomOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  glassesInfo: {
    alignItems: 'center',
  },
  glassesText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  glassesSubtext: {
    color: 'white',
    fontSize: 12,
    opacity: 0.8,
    marginTop: 4,
  },
  crosshair: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: 30,
    height: 30,
    marginTop: -15,
    marginLeft: -15,
  },
  crosshairHorizontal: {
    position: 'absolute',
    top: '50%',
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
  },
  crosshairVertical: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: '50%',
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    margin: 20,
  },
  buttonText: {
    color: 'white',
    textAlign: 'center',
    fontSize: 16,
    fontWeight: '600',
  },
});