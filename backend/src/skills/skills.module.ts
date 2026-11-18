import { Module } from '@nestjs/common';
import { AuthModule } from '../auth/auth.module.js';
import { ResumeModule } from '../resume/resume.module.js';
import { SkillsController } from './skills.controller.js';
import { SkillsService } from './skills.service.js';

@Module({
  imports: [AuthModule, ResumeModule],
  controllers: [SkillsController],
  providers: [SkillsService],
})
export class SkillsModule {}
