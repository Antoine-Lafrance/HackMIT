import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, Linking } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import * as Contacts from 'expo-contacts';
import { Audio } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface HomePageProps {}

export default function HomePage({ onOpenCamera, onOpenSettings }: HomePageProps) {

    const playAudioSegment = async (uri: string) => {
        try {
            const { sound } = await Audio.Sound.createAsync({ uri });
            await sound.playAsync();      
            sound.setOnPlaybackStatusUpdate((status) => {
                if (status.isLoaded && status.didJustFinish) {
                    sound.unloadAsync();
                }
            });
        } catch (error) {
            Alert.alert('Error', 'Failed to play audio clip');
        }
    };

    const playLatestAudio = async () => {
        try {
            const savedAudio = await AsyncStorage.getItem('audioSegments');
            if (savedAudio) {
                const audioData = JSON.parse(savedAudio);
                if (audioData.length > 0) {
                    const latest = audioData[audioData.length - 1];
                    await playAudioSegment(latest.uri);
                    Alert.alert('Audio', 'Playing latest recording...');
                } else {
                Alert.alert('No Audio', 'No audio recordings found');
                }
            } else {
                Alert.alert('No Audio', 'No audio recordings found');
            }
        } catch (error) {
            Alert.alert('Error', 'Failed to access audio recordings');
        }
    };

    const showAllAudioSegments = async () => {
    try {
        const savedAudio = await AsyncStorage.getItem('audioSegments');
        if (savedAudio) {
            const audioData = JSON.parse(savedAudio);
            if (audioData.length > 0) {
                Alert.alert(
                    'Audio Recordings',
                    `You have ${audioData.length} audio recording(s). Play the latest one?`,
                    [
                    { text: 'Cancel', style: 'cancel' },
                    { text: 'Play Latest', onPress: playLatestAudio }
                    ]
                );
            } else {
            Alert.alert('No Audio', 'No audio recordings found');
            }
        } else {
            Alert.alert('No Audio', 'No audio recordings found');
        }
    } catch (error) {
        Alert.alert('Error', 'Failed to access audio recordings');
    }
};

const handleCameraPress = () => {
    if (onOpenCamera) {
        onOpenCamera();
    } else {
        Alert.alert('Camera', 'Camera functionality will be implemented here');
    }
};

const handleContactCaretaker = async () => {
    try {
        const { status } = await Contacts.requestPermissionsAsync();
      
        if (status !== 'granted') {
            Alert.alert(
            'Permission Required', 
            'Please enable contacts access to find your caretaker.',
            [{ text: 'OK' }]
            );
            return;
        }

        const { data } = await Contacts.getContactsAsync({
            fields: [Contacts.Fields.Name, Contacts.Fields.PhoneNumbers],
            name: 'Caretaker'
        });

        if (data.length === 0) {
            Alert.alert(
                'Caretaker Not Found', 
                'No contact named "Caretaker" found. Please add a contact with this name.',
                [{ text: 'OK' }]
            );
            return;
        } 

        const caretaker = data[0];
        const phoneNumbers = caretaker.phoneNumbers;

        if (!phoneNumbers || phoneNumbers.length === 0) {
            Alert.alert(
                'No Phone Number', 
                'The caretaker contact does not have a phone number.',
                [{ text: 'OK' }]
            );
            return;
        }

        const phoneNumber = phoneNumbers[0].number;

        Alert.alert(
            'Call Caretaker',
            `Do you want to call ${caretaker.name || 'Caretaker'} at ${phoneNumber}?`,
            [
            { text: 'Cancel', style: 'cancel' },
            { 
                text: 'Call', 
                onPress: () => {
                // Make the phone call
                const phoneUrl = `tel:${phoneNumber}`;
                Linking.openURL(phoneUrl);
                }
            }
            ]
        );
    } catch (error) {
        console.error('Error accessing contacts:', error);
        Alert.alert(
            'Error', 
            'Unable to access contacts. Please try again.',
            [{ text: 'OK' }]
        );
    }
};

return (
    <LinearGradient
        colors={['#1a0033', '#4a0080', '#8a2be2', '#9932cc']}
        style={styles.container}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 1 }}
    >
        <View style={styles.content}>
            <Text style={styles.title}>Welcome to Mementor</Text>
            <Text style={styles.subtitle}>Your aid to dementia</Text>

            {/* Face recognition is handled by agent system - no frontend needed */}

            <View style={styles.featuresSection}>
                <Text style={styles.featuresTitle}>Features</Text>
                
                <TouchableOpacity 
                style={styles.featureItem}
                onPress={showAllAudioSegments}
                activeOpacity={0.7}
                >
                <Ionicons name="play-circle-outline" size={24} color="white" />
                <Text style={styles.featureText}>Play Audio Recordings</Text>
                </TouchableOpacity>
                
                <View style={styles.featureItem}>
                <Ionicons name="images-outline" size={24} color="white" />
                <Text style={styles.featureText}>Weekly Review</Text>
                </View>
                
                <View style={styles.featureItem}>
                <Ionicons name="calendar-outline" size={24} color="white" />
                <Text style={styles.featureText}>Task Upload</Text>
                </View>
                
                <TouchableOpacity 
                style={styles.featureItem}
                onPress={handleContactCaretaker}
                activeOpacity={0.7}
                >
                <Ionicons name="call-outline" size={24} color="white" />
                <Text style={styles.featureText}>Contact caretaker</Text>
                </TouchableOpacity>
            </View>
        </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    content: {
        flex: 1,
        padding: 20,
        paddingTop: 60,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 40,
    },
    titleContainer: {
        flex: 1,
    },
    title: {
        fontSize: 32,
        fontWeight: 'bold',
        textAlign: 'center',
        marginBottom: 8,
        color: '#fff',
    },
    subtitle: {
        fontSize: 16,
        textAlign: 'center',
        marginBottom: 0,
        color: '#ddd',
    },
    featuresSection: {
        flex: 1,
        paddingTop: 20,
    },
    featuresTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#fff',
        marginBottom: 20,
        textAlign: 'center',
    },
    featureItem: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.2)',
    },
    featureText: {
        color: 'white',
        fontSize: 16,
        marginLeft: 12,
        fontWeight: '500',
    },
});