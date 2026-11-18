import { Module } from '@nestjs/common';
import { ResumeService } from './resume.service.js';

@Module({
  providers: [ResumeService],
  exports: [ResumeService],
})
export class ResumeModule {}
