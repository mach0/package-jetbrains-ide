#!/bin/sh

paths="
/usr/lib/jvm/default-java
/usr/lib/jvm/java-17-openjdk-amd64
/usr/lib/jvm/java-17-openjre-amd64
/usr/lib/jvm/java-11-openjdk-amd64
/usr/lib/jvm/java-11-openjre-amd64
/usr/lib/jvm/java-14-openjdk-amd64
/usr/lib/jvm/java-14-openjre-amd64
/usr/lib/jvm/java-8-oracle
/usr/lib/jvm/java-8-openjdk
/usr/lib/jvm/java-8-openjdk/jre
/usr/lib/jvm/java-8-openjdk-amd64
/usr/lib/jvm/java-8-openjdk-amd64/jre
/usr/lib/jvm/java-7-openjdk
/usr/lib/jvm/java-7-openjdk/jre
/usr/lib/jvm/java-7-openjdk-amd64
/usr/lib/jvm/java-7-openjdk-amd64/jre
/usr/jdk/instances/jdk1.7.0
/usr/jdk/instances/jdk1.6.0
/usr/lib/jvm/java-6-sun
/usr/lib/jvm/java-6-openjdk
/usr/lib/jvm/java-6-openjdk/jre
/usr/lib/jvm/java-6-openjdk-amd64
/usr/lib/jvm/java-6-openjdk-amd64/jre
/usr/jdk/instances/jdk1.5.0
/usr/lib/jvm/java-5-sun"

if [ -r /etc/default/APPNAME ]
then
  . /etc/default/APPNAME
fi

if [ -z "$JDK_HOME" ]
then
  for path in $paths
  do
    if [ -x $path/bin/java ]
    then
      JDK_HOME=$path
      break
    fi
  done
fi

if [ -z "$JDK_HOME" ]
then
  echo "Could not find a suitable JDK installation amongst:" >/dev/stderr
  for path in $paths
  do
    echo $path >/dev/stderr
  done
  echo "Either install a JDK in one of those locations or configure JDK_HOME in /etc/default/idea:" >/dev/stderr
  exit 1
fi

echo "JDK_HOME=$JDK_HOME"
export JDK_HOME

if [ -z "$IDEA_VM_OPTIONS" ]
then
  if [ -r "$HOME/.APPNAME.vmoptions" ]
  then
    IDEA_VM_OPTIONS="$HOME/.APPNAME.vmoptions"
    export IDEA_VM_OPTIONS
  else
    if [ -r "/etc/intellij-idea/APPNAME.vmoptions" ]
    then
      IDEA_VM_OPTIONS="/etc/intellij-idea/APPNAME.vmoptions"
      export IDEA_VM_OPTIONS
    fi
  fi
fi

exec /usr/share/jetbrains/APPNAME/bin/idea.sh "$@"

