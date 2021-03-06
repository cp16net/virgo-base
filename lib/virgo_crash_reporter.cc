/*
 *  Copyright 2012 Rackspace
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */

#define DEMARCATOR \
  "__5FY97Y1WBU7GPXCSIRS3T2EEHTSNJ6W183N8FUBFOD5LDWW06ZRBQB8AA8LA8BJD__"

extern "C" {
  #include "virgo__util.h"
  #include "virgo__types.h"
  #include "virgo_brand.h"
  #include "virgo_paths.h"
  #include "virgo.h"
  #include "stdio.h"

};

#include "../deps/breakpad/src/client/linux/handler/exception_handler.h"

google_breakpad::ExceptionHandler *virgo_global_exception_handler = NULL;

static bool dumpCallback(const char* dump_path, const char* minidump_id, void* context, bool succeeded) {
  int rv;
  FILE *fp;
  char *dump_file = NULL;
  virgo_t* v;
  lua_State *L;

  rv = asprintf((char **) &dump_file, "%s/%s-crash-report-%s.dmp", dump_path, VIRGO_DEFAULT_NAME, minidump_id);
  if (rv != -1){
    printf("FATAL ERROR: Crash Dump written to: %s\n", dump_file);
  }

  v = (virgo_t *)context;
  if (v == NULL) {
    printf("NULL virgo context in dumpCallback");
    return succeeded;
  }

  fp = fopen(dump_file, "ab");
  if (fp == NULL) {
    return succeeded;
  }
  fprintf(fp, "%s\n%s", DEMARCATOR, VERSION_FULL);

  v = *(virgo_t **)context;
  L = v->L;

  if (!L){
    printf("No lua found.");
    fclose(fp);
    return succeeded;
  }
  lua_getglobal(L, "dump_lua");
  rv = lua_pcall(L, 0, 1, 0);
  if (rv != 0) {
    printf("Error with lua dump: %s\n", lua_tostring(L, -1));
    fclose(fp);
    return succeeded;
  }

  fprintf(fp, "%s\n%s", DEMARCATOR, lua_tostring(L, -1));
  fclose(fp);

  return succeeded;
}

extern "C" {

  char path[VIRGO_PATH_MAX];

  virgo_t *v = NULL;
  virgo_error_t *err = virgo__paths_get(v, VIRGO_PATH_PERSISTENT_DIR, path, VIRGO_PATH_MAX);

  void virgo__crash_reporter_init(virgo_t *v) {
    if (virgo__argv_has_flag(v, NULL, "--production") == 1){
      virgo_global_exception_handler = new google_breakpad::ExceptionHandler(path, NULL, dumpCallback, (void *)v, true);
    }
  };

  void virgo__force_dump() {
    if (virgo_global_exception_handler){
      virgo_global_exception_handler->WriteMinidump();
    }
  };

  void virgo__crash_reporter_destroy() {
    if (virgo_global_exception_handler){
      delete virgo_global_exception_handler;
    }
  };
};

