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
  }

  async initialize(): Promise<void> {
    if (this.modelsLoaded) return;

    try {
      console.log('Initializing Python face recognition service...');
      
      // Test connection to Python service
      const response = await fetch(`${this.pythonServiceUrl}/health`);
      if (!response.ok) {
        throw new Error(`Python service not available: ${response.status}`);
      }
      
      this.modelsLoaded = true;
      console.log('✅ Python face recognition service ready');
    } catch (error) {
      console.error('Failed to connect to Python face recognition service:', error);
      throw new Error('Python face recognition service could not be initialized');
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

  async recognizeFace(base64Image: string): Promise<FaceRecognitionResult> {
    try {
      // Initialize service if needed
      if (!this.modelsLoaded) {
        await this.initialize();
      }

      // Process the image
      const imageBuffer = await this.processImage(base64Image);

      // Detect faces using Python service
      const faceDetections = await this.detectFaces(imageBuffer);

      if (faceDetections.length === 0) {
        return {
          success: false,
          message: 'No faces detected in the image'
        };
      }

      // For now, process the first detected face
      const face = faceDetections[0];

      // Try to identify the face using database
      const identifiedFace = await this.identifyFace(face.embedding);

      if (identifiedFace) {
        return {
          success: true,
          person: identifiedFace.name,
          relationship: identifiedFace.relationship,
          confidence: face.confidence,
          color: identifiedFace.color,
          message: `Recognized ${identifiedFace.name} (${identifiedFace.relationship})`
        };
      } else {
        return {
          success: false,
          person: 'Unknown',
          relationship: 'Unknown',
          confidence: face.confidence,
          message: 'Face detected but not recognized. Consider adding this person to the database.'
        };
      }
    } catch (error) {
      console.error('Error in face recognition:', error);
      return {
        success: false,
        message: 'Face recognition failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
}

// Export singleton instance
export const pythonFaceRecognitionService = new PythonFaceRecognitionService();
