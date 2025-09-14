import { supabase, FaceRecord, FaceInsert, FaceUpdate } from './supabase.js';

interface FaceRecognitionResult {
  success: boolean;
  person?: string;
  relationship?: string;
  confidence?: number;
  color?: string;
  message: string;
  error?: string;
}

interface FaceDetection {
  name: string;
  relationship: string;
  color: string;
  embedding: number[];
  confidence: number;
}

interface PythonFaceResponse {
  success: boolean;
  person?: string;
  relationship?: string;
  confidence?: number;
  color?: string;
  message: string;
  error?: string;
}

interface PythonFaceDetectionResponse {
  success: boolean;
  faces: Array<{
    face_id: string;
    encoding: number[];
    location: {
      top: number;
      right: number;
      bottom: number;
      left: number;
    };
    confidence: number;
    name: string;
    relationship: string;
    color: string;
  }>;
  message: string;
  error?: string;
}

class PythonFaceRecognitionService {
  private pythonServiceUrl: string;
  private modelsLoaded = false;

  constructor() {
    this.pythonServiceUrl = process.env.PYTHON_FACE_SERVICE_URL || 'http://localhost:8001';
    console.log(`Python face service URL: ${this.pythonServiceUrl}`);
  }

  async initialize(): Promise<void> {
    if (this.modelsLoaded) return;

    try {
      console.log('Initializing Python face recognition service...');
      
      // Test connection to Python service with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
      
      const response = await fetch(`${this.pythonServiceUrl}/health`, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`Python service not available: ${response.status} ${response.statusText}`);
      }
      
      this.modelsLoaded = true;
      console.log('✅ Python face recognition service ready');
    } catch (error) {
      console.error('Failed to connect to Python face recognition service:', error);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Python face recognition service connection timeout - is the service running?');
      }
      throw new Error(`Python face recognition service could not be initialized: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async processImage(base64Image: string): Promise<Buffer> {
    try {
      // Remove data URL prefix if present
      const base64Data = base64Image.replace(/^data:image\/[a-z]+;base64,/, '');
      return Buffer.from(base64Data, 'base64');
    } catch (error) {
      console.error('Error processing image:', error);
      throw new Error('Failed to process image');
    }
  }

  async detectFaces(imageBuffer: Buffer): Promise<FaceDetection[]> {
    try {
      if (!this.modelsLoaded) {
        await this.initialize();
      }

      // Convert buffer to base64
      const base64Image = imageBuffer.toString('base64');
      
      // Call Python service for face detection
      const response = await fetch(`${this.pythonServiceUrl}/detect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_data: base64Image,
          operation: 'detect'
        })
      });

      if (!response.ok) {
        throw new Error(`Python service error: ${response.status}`);
      }

      const result: PythonFaceDetectionResponse = await response.json();
      
      if (!result.success) {
        console.error('Python face detection failed:', result.error);
        return [];
      }

      // Convert Python response to our format
      const faceDetections: FaceDetection[] = result.faces.map(face => ({
        name: face.name,
        relationship: face.relationship,
        color: face.color,
        embedding: face.encoding, // Python uses 'encoding', we use 'embedding'
        confidence: face.confidence
      }));

      console.log(`Detected ${faceDetections.length} faces via Python service`);
      return faceDetections;
      
    } catch (error) {
      console.error('Error detecting faces:', error);
      return [];
    }
  }

  async identifyFace(embedding: number[]): Promise<FaceRecord | null> {
    try {
      // Query database for similar faces using vector similarity
      const { data, error } = await supabase.rpc('match_faces', {
        query_embedding: embedding,
        match_threshold: 0.7, // Cosine similarity threshold
        match_count: 1
      });

      if (error) {
        console.error('Database error during face matching:', error);
        return null;
      }

      if (data && data.length > 0) {
        return data[0] as FaceRecord;
      }

      return null;
    } catch (error) {
      console.error('Error identifying face:', error);
      return null;
    }
  }

  async addFace(faceData: FaceInsert): Promise<FaceRecord | null> {
    try {
      const { data, error } = await supabase
        .from('faces')
        .insert([faceData])
        .select()
        .single();

      if (error) {
        console.error('Error adding face to database:', error);
        return null;
      }

      return data as FaceRecord;
    } catch (error) {
      console.error('Error adding face:', error);
      return null;
    }
  }

  async updateFace(id: string, updates: FaceUpdate): Promise<FaceRecord | null> {
    try {
      const { data, error } = await supabase
        .from('faces')
        .update(updates)
        .eq('id', id)
        .select()
        .single();

      if (error) {
        console.error('Error updating face in database:', error);
        return null;
      }

      return data as FaceRecord;
    } catch (error) {
      console.error('Error updating face:', error);
      return null;
    }
  }

  async getAllFaces(userId?: string): Promise<FaceRecord[]> {
    try {
      let query = supabase.from('faces').select('*');
      
      if (userId) {
        query = query.eq('user_id', userId);
      }

      const { data, error } = await query;

      if (error) {
        console.error('Error fetching faces from database:', error);
        return [];
      }

      return data as FaceRecord[];
    } catch (error) {
      console.error('Error fetching faces:', error);
      return [];
    }
  }

  async recognizeFace(base64Image: string, personName?: string, personRelationship?: string): Promise<FaceRecognitionResult> {
    try {
      // Initialize service if needed
      if (!this.modelsLoaded) {
        await this.initialize();
      }

      // Validate image data
      if (!base64Image || base64Image.trim().length === 0) {
        return {
          success: false,
          message: 'No image data provided',
          error: 'Empty image data'
        };
      }

      // Step 1: Get face detection from Python service
      const faceDetections = await this.detectFaces(Buffer.from(base64Image, 'base64'));
      
      if (faceDetections.length === 0) {
        return {
          success: false,
          message: 'No faces detected in the image',
          error: 'No faces found'
        };
      }

      // Step 2: Use the first detected face for recognition
      const face = faceDetections[0];
      
      // Step 3: Search for existing person in Supabase
      const existingPerson = await this.identifyFace(face.embedding);
      
      if (existingPerson) {
        // Person found in database
        return {
          success: true,
          person: existingPerson.name,
          relationship: existingPerson.relationship,
          confidence: 0.8, // Default confidence for database matches
          color: existingPerson.color,
          message: `Found existing person: ${existingPerson.name} (${existingPerson.relationship})`
        };
      } else {
        // Person not found, add new person if name/relationship provided
        if (personName && personRelationship) {
          const newFace = await this.addFace({
            name: personName,
            relationship: personRelationship,
            face_embedding: face.embedding,
            color: this.getRandomColor()
          });
          
          if (newFace) {
            return {
              success: true,
              person: newFace.name,
              relationship: newFace.relationship,
              confidence: 1.0,
              color: newFace.color,
              message: `Added new person: ${newFace.name} (${newFace.relationship})`
            };
          }
        }
        
        return {
          success: false,
          person: 'Unknown',
          relationship: 'Unknown',
          confidence: face.confidence,
          message: 'Face detected but not recognized. Provide name and relationship to add new person.'
        };
      }
    } catch (error) {
      console.error('Error in face recognition:', error);
      
      let errorMessage = 'Face recognition failed';
      if (error instanceof Error) {
        if (error.message.includes('fetch')) {
          errorMessage = 'Cannot connect to Python face recognition service - is it running?';
        } else {
          errorMessage = error.message;
        }
      }
      
      return {
        success: false,
        message: errorMessage,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  private getRandomColor(): string {
    const hexColors = [
      '#FF6B6B',  // Red
      '#4ECDC4',  // Teal
      '#45B7D1',  // Blue
      '#96CEB4',  // Green
      '#FFEAA7',  // Yellow
      '#DDA0DD',  // Plum
      '#FFB6C1',  // Light Pink
      '#98D8C8',  // Mint
      '#F7DC6F',  // Gold
      '#BB8FCE',  // Lavender
      '#85C1E9',  // Sky Blue
      '#F8C471',  // Orange
    ];
    return hexColors[Math.floor(Math.random() * hexColors.length)];
  }
}

// Export singleton instance
export const pythonFaceRecognitionService = new PythonFaceRecognitionService();
