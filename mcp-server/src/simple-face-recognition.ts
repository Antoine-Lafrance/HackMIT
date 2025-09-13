import { supabase, FaceRecord, FaceInsert } from './supabase.js';

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

class SimpleFaceRecognitionService {
  private modelsLoaded = false;

  async initialize(): Promise<void> {
    if (this.modelsLoaded) return;

    try {
      console.log('Initializing simple face recognition service...');
      
      // For hackathon purposes, we'll use a simple mock implementation
      // This creates deterministic "embeddings" based on image content
      console.log('✅ Simple face recognition service ready');
      console.log('📝 Note: This is a demo implementation for hackathon purposes');
      
      this.modelsLoaded = true;
    } catch (error) {
      console.error('Failed to initialize face recognition service:', error);
      throw new Error('Face recognition service could not be initialized');
    }
  }

  async processImage(base64Image: string): Promise<Buffer> {
    try {
      // Remove data URL prefix if present
      const base64Data = base64Image.replace(/^data:image\/[a-z]+;base64,/, '');
      const imageBuffer = Buffer.from(base64Data, 'base64');
      
      // For demo purposes, we'll just return the buffer as-is
      // In a real implementation, you might resize or optimize the image
      return imageBuffer;
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

      // For hackathon demo: create a deterministic "embedding" based on image content
      // This simulates face detection without requiring complex ML libraries
      console.log('🔍 Simulating face detection...');
      
      // Create a simple hash-based embedding from the image buffer
      const imageHash = this.simpleHash(imageBuffer);
      const mockEmbedding = this.generateMockEmbedding(imageHash);
      
      return [{
        name: 'Unknown',
        relationship: 'Unknown',
        color: 'gray',
        embedding: mockEmbedding,
        confidence: 0.85 // Mock confidence
      }];
      
    } catch (error) {
      console.error('Error detecting faces:', error);
      return [];
    }
  }

  private simpleHash(buffer: Buffer): number {
    // Simple hash function for demo purposes
    let hash = 0;
    for (let i = 0; i < Math.min(buffer.length, 1000); i++) {
      hash = ((hash << 5) - hash + buffer[i]) & 0xffffffff;
    }
    return Math.abs(hash);
  }

  private generateMockEmbedding(seed: number): number[] {
    // Generate a deterministic 512-dimensional embedding based on the seed
    const embedding = [];
    for (let i = 0; i < 512; i++) {
      // Use a simple pseudo-random generator seeded with the image hash
      const x = Math.sin(seed + i) * 10000;
      embedding.push(x - Math.floor(x));
    }
    return embedding;
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
      // Initialize models if needed
      if (!this.modelsLoaded) {
        await this.initialize();
      }

      // Process the image
      const imageBuffer = await this.processImage(base64Image);

      // Detect faces
      const faceDetections = await this.detectFaces(imageBuffer);

      if (faceDetections.length === 0) {
        return {
          success: false,
          message: 'No faces detected in the image'
        };
      }

      // For now, process the first detected face
      const face = faceDetections[0];

      // Try to identify the face
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
export const simpleFaceRecognitionService = new SimpleFaceRecognitionService();