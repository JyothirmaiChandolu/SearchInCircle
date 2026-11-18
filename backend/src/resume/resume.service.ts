import { BadRequestException, Injectable } from '@nestjs/common';
import { PDFParse } from 'pdf-parse';
import { SKILL_DICTIONARY } from './skill-dictionary.js';

const SUPPORTED_MIME_TYPES = new Set(['application/pdf', 'text/plain']);

@Injectable()
export class ResumeService {
  /** Extracts text from an uploaded resume (PDF or plain text) and returns dictionary
   * skills/tools found in it. Nothing is persisted here — this is suggestions only. */
  async suggestSkills(file: { buffer: Buffer; mimetype: string }): Promise<string[]> {
    if (!SUPPORTED_MIME_TYPES.has(file.mimetype)) {
      throw new BadRequestException('Resume must be a PDF or plain text file.');
    }

    const text =
      file.mimetype === 'application/pdf'
        ? (await new PDFParse({ data: file.buffer }).getText()).text
        : file.buffer.toString('utf-8');

    const lowerText = text.toLowerCase();
    return SKILL_DICTIONARY.filter((skill) => {
      const pattern = new RegExp(`\\b${escapeRegExp(skill.toLowerCase())}\\b`);
      return pattern.test(lowerText);
    });
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
