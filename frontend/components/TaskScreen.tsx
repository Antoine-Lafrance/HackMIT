import React, { useState, useEffect } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    TouchableOpacity, 
    StyleSheet, 
    Alert, 
    ScrollView,
    FlatList 
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface Task {
    id: string;
    date: string;
    time: string;
    description: string;
    completed: boolean;
    created: string;
}

interface TaskScreenProps {
    onClose?: () => void;
}

export default function TaskScreen({ onClose }: TaskScreenProps) {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [description, setDescription] = useState('');
    const [dateInput, setDateInput] = useState('');
    const [timeInput, setTimeInput] = useState('');

    useEffect(() => {
        loadTasks();
        // Set default date to today and time to current hour
        const now = new Date();
        setDateInput(now.toISOString().split('T')[0]); // YYYY-MM-DD format
        setTimeInput(now.toTimeString().split(':').slice(0, 2).join(':')); // HH:MM format
    }, []);

    const loadTasks = async () => {
        try {
            const savedTasks = await AsyncStorage.getItem('tasks');
            if (savedTasks) {
                const tasksData = JSON.parse(savedTasks);
                setTasks(tasksData);
            }
        } catch (error) {
            console.error('Failed to load tasks:', error);
        }
    };

    const saveTasks = async (newTasks: Task[]) => {
        try {
            await AsyncStorage.setItem('tasks', JSON.stringify(newTasks));
            setTasks(newTasks);
        } catch (error) {
            console.error('Failed to save tasks:', error);
            Alert.alert('Error', 'Failed to save task. Please try again.');
        }
    };

    const addTask = () => {
        if (!description.trim()) {
            Alert.alert('Error', 'Please enter a task description.');
            return;
        }

        if (!dateInput.trim()) {
            Alert.alert('Error', 'Please enter a date (YYYY-MM-DD).');
            return;
        }

        if (!timeInput.trim()) {
            Alert.alert('Error', 'Please enter a time (HH:MM).');
            return;
        }

        // Validate date format
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        if (!dateRegex.test(dateInput)) {
            Alert.alert('Error', 'Please enter date in YYYY-MM-DD format.');
            return;
        }

        // Validate time format
        const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
        if (!timeRegex.test(timeInput)) {
            Alert.alert('Error', 'Please enter time in HH:MM format.');
            return;
        }

        const newTask: Task = {
            id: Date.now().toString(),
            date: dateInput,
            time: timeInput,
            description: description.trim(),
            completed: false,
            created: new Date().toISOString()
        };

        const updatedTasks = [...tasks, newTask];
        saveTasks(updatedTasks);
        setDescription('');
        
        Alert.alert('Success', 'Task added successfully!');
    };

    const deleteTask = (taskId: string) => {
        Alert.alert(
            'Delete Task',
            'Are you sure you want to delete this task?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Delete',
                    style: 'destructive',
                    onPress: () => {
                        const updatedTasks = tasks.filter(task => task.id !== taskId);
                        saveTasks(updatedTasks);
                    }
                }
            ]
        );
    };

    const toggleTaskCompletion = (taskId: string) => {
        const updatedTasks = tasks.map(task =>
            task.id === taskId ? { ...task, completed: !task.completed } : task
        );
        saveTasks(updatedTasks);
    };

    const renderTask = ({ item }: { item: Task }) => (
        <View style={[styles.taskItem, item.completed && styles.completedTask]}>
            <TouchableOpacity 
                style={styles.taskContent}
                onPress={() => toggleTaskCompletion(item.id)}
            >
                <View style={styles.taskHeader}>
                    <Text style={[styles.taskDate, item.completed && styles.completedText]}>
                        {item.date} at {item.time}
                    </Text>
                    <Ionicons 
                        name={item.completed ? "checkmark-circle" : "ellipse-outline"} 
                        size={24} 
                        color={item.completed ? "#4CAF50" : "#666"} 
                    />
                </View>
                <Text style={[styles.taskDescription, item.completed && styles.completedText]}>
                    {item.description}
                </Text>
            </TouchableOpacity>
            <TouchableOpacity 
                style={styles.deleteButton}
                onPress={() => deleteTask(item.id)}
            >
                <Ionicons name="trash-outline" size={20} color="#FF6B6B" />
            </TouchableOpacity>
        </View>
    );

    return (
        <LinearGradient
            colors={['#667eea', '#764ba2']}
            style={styles.container}
        >
            <View style={styles.header}>
                <Text style={styles.title}>Task Reminders</Text>
                <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                    <Ionicons name="close" size={24} color="white" />
                </TouchableOpacity>
            </View>

            <ScrollView style={styles.content}>
                {/* Add Task Form */}
                <View style={styles.formSection}>
                    <Text style={styles.sectionTitle}>Add New Task</Text>
                    
                    <View style={styles.dateTimeContainer}>
                        <View style={styles.inputContainer}>
                            <Ionicons name="calendar-outline" size={20} color="white" />
                            <TextInput
                                style={styles.dateTimeInput}
                                placeholder="YYYY-MM-DD"
                                placeholderTextColor="#aaa"
                                value={dateInput}
                                onChangeText={setDateInput}
                            />
                        </View>

                        <View style={styles.inputContainer}>
                            <Ionicons name="time-outline" size={20} color="white" />
                            <TextInput
                                style={styles.dateTimeInput}
                                placeholder="HH:MM"
                                placeholderTextColor="#aaa"
                                value={timeInput}
                                onChangeText={setTimeInput}
                            />
                        </View>
                    </View>

                    <TextInput
                        style={styles.descriptionInput}
                        placeholder="Enter task description..."
                        placeholderTextColor="#aaa"
                        value={description}
                        onChangeText={setDescription}
                        multiline
                        numberOfLines={3}
                    />

                    <TouchableOpacity style={styles.addButton} onPress={addTask}>
                        <Text style={styles.addButtonText}>Add Task</Text>
                    </TouchableOpacity>
                </View>

                {/* Tasks List */}
                <View style={styles.tasksSection}>
                    <Text style={styles.sectionTitle}>Your Tasks ({tasks.length})</Text>
                    {tasks.length === 0 ? (
                        <Text style={styles.noTasksText}>No tasks yet. Add one above!</Text>
                    ) : (
                        <FlatList
                            data={tasks.sort((a, b) => new Date(a.date + ' ' + a.time).getTime() - new Date(b.date + ' ' + b.time).getTime())}
                            renderItem={renderTask}
                            keyExtractor={(item) => item.id}
                            scrollEnabled={false}
                        />
                    )}
                </View>
            </ScrollView>
        </LinearGradient>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: 50,
        paddingHorizontal: 20,
        paddingBottom: 20,
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: 'white',
    },
    closeButton: {
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderRadius: 20,
        padding: 8,
    },
    content: {
        flex: 1,
        paddingHorizontal: 20,
    },
    formSection: {
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        borderRadius: 15,
        padding: 20,
        marginBottom: 20,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 15,
    },
    dateTimeContainer: {
        flexDirection: 'row',
        gap: 10,
        marginBottom: 15,
    },
    inputContainer: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderRadius: 10,
        padding: 12,
        gap: 8,
    },
    dateTimeInput: {
        flex: 1,
        color: 'white',
        fontSize: 14,
        fontWeight: '500',
    },
    dateTimeButton: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderRadius: 10,
        padding: 12,
        gap: 8,
    },
    dateTimeText: {
        color: 'white',
        fontSize: 14,
        fontWeight: '500',
    },
    descriptionInput: {
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderRadius: 10,
        padding: 15,
        fontSize: 16,
        textAlignVertical: 'top',
        marginBottom: 15,
    },
    addButton: {
        backgroundColor: '#4CAF50',
        borderRadius: 10,
        padding: 15,
        alignItems: 'center',
    },
    addButtonText: {
        color: 'white',
        fontSize: 16,
        fontWeight: 'bold',
    },
    tasksSection: {
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        borderRadius: 15,
        padding: 20,
        marginBottom: 20,
    },
    noTasksText: {
        color: 'rgba(255, 255, 255, 0.7)',
        textAlign: 'center',
        fontStyle: 'italic',
        marginTop: 10,
    },
    taskItem: {
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderRadius: 10,
        padding: 15,
        marginBottom: 10,
        flexDirection: 'row',
        alignItems: 'center',
    },
    completedTask: {
        backgroundColor: 'rgba(255, 255, 255, 0.5)',
    },
    taskContent: {
        flex: 1,
    },
    taskHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 5,
    },
    taskDate: {
        fontSize: 12,
        color: '#666',
        fontWeight: '500',
    },
    taskDescription: {
        fontSize: 14,
        color: '#333',
    },
    completedText: {
        textDecorationLine: 'line-through',
        opacity: 0.6,
    },
    deleteButton: {
        marginLeft: 10,
        padding: 5,
    },
});