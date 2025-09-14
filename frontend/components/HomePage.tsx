import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, Linking } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import * as Contacts from 'expo-contacts';

interface HomePageProps {
    onOpenCamera?: () => void;
    onOpenSettings?: () => void;
}

export default function HomePage({ onOpenCamera, onOpenSettings }: HomePageProps) {

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
            <View style={styles.header}>
                <View style={styles.titleContainer}>
                    <Text style={styles.title}>Welcome to Mementor</Text>
                    <Text style={styles.subtitle}>Your aid to dementia</Text>
                </View>
                <TouchableOpacity 
                    style={styles.settingsButton}
                    onPress={onOpenSettings}
                    activeOpacity={0.8}
                >
                    <Ionicons name="settings-outline" size={24} color="white" />
                </TouchableOpacity>
            </View>

            <View style={styles.cameraSection}>
                <TouchableOpacity 
                style={styles.cameraButton}
                onPress={handleCameraPress}
                activeOpacity={0.8}
                >
                <Ionicons name="camera" size={40} color="white" />
                <Text style={styles.cameraButtonText}>Open Camera</Text>
                </TouchableOpacity>
            </View>

            <View style={styles.featuresSection}>
                <Text style={styles.featuresTitle}>Features</Text>
                
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
    settingsButton: {
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.3)',
        borderRadius: 20,
        padding: 12,
        marginTop: 5,
    },
    cameraSection: {
        alignItems: 'center',
        marginBottom: 40,
    },
    cameraButton: {
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 2,
        borderColor: 'rgba(255, 255, 255, 0.3)',
        borderRadius: 20,
        padding: 30,
        alignItems: 'center',
        justifyContent: 'center',
        minWidth: 200,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 10,
        elevation: 8,
    },
    cameraButtonText: {
        color: 'white',
        fontSize: 18,
        fontWeight: '600',
        marginTop: 10,
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